"""Fill the scan test sheets with marks that look handwritten, so that a first scan test needs no pen.

Usage:
    python tools/fill_test_sheet.py fill <sheets.pdf> <filled.pdf> [--seed N]
        draws into the sheets written by ``scan_test.py make`` what the instruction sheet asks for:
        crosses, ticks, small and large crosses, blackened boxes, half strokes, faint and erased
        pencil, a circled box, felt-tip crosses, and the student numbers written and ticked
    python tools/fill_test_sheet.py simulate <filled.pdf> <scan.pdf> [--seed N]
        turns the filled sheets into a scan as a copier would deliver it: 300 dpi greyscale, slightly
        turned, shifted and blurred, with noise and grey paper, the second sheet upside down

The marks are drawn as vector strokes with a little irregularity, so that they print sharply and
the copier's scan is the only source of blur. Which box gets which mark comes from PLAN in
scan_test.py, so that the comparison in ``scan_test.py read`` fits. All data is invented.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import cv2
import numpy as np
import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from scan_test import PLAN, STUDENT_NUMBERS, UPSIDE_DOWN_BOOKLET  # noqa: E402

from markwise.scan import DOUBTFUL, TICKED  # noqa: E402
from markwise.sheet import build_layout  # noqa: E402

MM = 72 / 25.4  # points per millimetre

# Pens: colour (RGB 0..1), stroke width in mm, opacity.
BALLPOINT = {"001": ((0.12, 0.18, 0.55), 0.42, 1.0), "002": ((0.09, 0.09, 0.11), 0.40, 1.0)}
PENCIL = ((0.30, 0.30, 0.32), 0.32, 0.9)
FAINT_PENCIL = ((0.62, 0.62, 0.64), 0.24, 0.55)
ERASED = ((0.84, 0.84, 0.85), 0.34, 0.55)
FELT = ((0.05, 0.05, 0.06), 1.0, 1.0)
HANDWRITING_FONT = Path("C:/Windows/Fonts/Inkfree.ttf")

# The mark per line of the plan, in its order (see PLAN in scan_test.py).
STYLES = ["cross", "cross", "tick", "small", "large", "filled", "correction", "half", "faint", "pencil",
          "erased", "circle", "felt", "none"]


class Pen:
    """Draws slightly irregular strokes on one page."""

    def __init__(self, page: pymupdf.Page, rng: np.random.Generator):
        self.page = page
        self.rng = rng

    def line(self, points_mm: list[tuple[float, float]], pen: tuple, wobble: float = 0.05) -> None:
        colour, width, opacity = pen
        pts = [pymupdf.Point((x + self.rng.normal(0, wobble)) * MM, (y + self.rng.normal(0, wobble)) * MM)
               for x, y in points_mm]
        shape = self.page.new_shape()
        shape.draw_polyline(pts)
        shape.finish(color=colour, width=width * MM * self.rng.uniform(0.9, 1.1), closePath=False,
                     lineCap=1, lineJoin=1, stroke_opacity=opacity)
        shape.commit()

    def stroke(self, start, end, pen, bow: float | None = None) -> None:
        """A stroke from start to end that bends a little, as a hand draws it."""
        (x0, y0), (x1, y1) = start, end
        bow = self.rng.normal(0, 0.18) if bow is None else bow
        length = math.hypot(x1 - x0, y1 - y0) or 1.0
        nx, ny = -(y1 - y0) / length, (x1 - x0) / length
        pts = []
        for i in range(14):
            t = i / 13
            b = 4 * t * (1 - t) * bow
            pts.append((x0 + (x1 - x0) * t + nx * b, y0 + (y1 - y0) * t + ny * b))
        self.line(pts, pen, wobble=0.025)


def _turn(points, centre, angle):
    cx, cy = centre
    c, s = math.cos(angle), math.sin(angle)
    return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in points]


def cross(pen: Pen, centre, box: float, ink, scale: float = 1.0) -> None:
    rng = pen.rng
    h = box / 2 * scale * rng.uniform(0.78, 0.98)
    centre = (centre[0] + rng.normal(0, 0.25), centre[1] + rng.normal(0, 0.25))
    angle = math.radians(rng.normal(0, 7))
    j = lambda: rng.normal(0, 0.12 * h)  # noqa: E731
    a = _turn([(-h + j(), -h + j()), (h + j(), h + j())], centre, angle)
    b = _turn([(h + j(), -h + j()), (-h + j(), h + j())], centre, angle)
    pen.stroke(a[0], a[1], ink)
    pen.stroke(b[0], b[1], ink)


def tick(pen: Pen, centre, box: float, ink) -> None:
    rng = pen.rng
    h = box / 2 * rng.uniform(0.85, 1.0)
    pts = _turn([(-0.55 * h, 0.0), (-0.1 * h, 0.5 * h), (0.7 * h, -0.85 * h)], centre, math.radians(rng.normal(0, 6)))
    pen.stroke(pts[0], pts[1], ink, bow=0.05)
    pen.stroke(pts[1], pts[2], ink, bow=-0.15)


def half_stroke(pen: Pen, centre, box: float, ink) -> None:
    h = box / 2
    pts = _turn([(-0.55 * h, -0.05 * h), (-0.1 * h, 0.45 * h)], centre, math.radians(pen.rng.normal(0, 8)))
    pen.stroke(pts[0], pts[1], ink, bow=0.03)


def blacken(pen: Pen, centre, box: float, ink) -> None:
    """First a cross, then the box scribbled over until it is dark, as a student corrects an answer."""
    cross(pen, centre, box, ink)
    rng = pen.rng
    colour, width, opacity = ink
    hatch = (colour, 0.55, opacity)
    h = box / 2 - 0.35
    for angle in (rng.uniform(20, 40), rng.uniform(-50, -30)):
        a = math.radians(angle)
        pts = []
        steps = int(2 * h / 0.32) + 2
        for i in range(steps):
            off = -h * 1.45 + i * (2.9 * h / steps)
            ends = [(-1.6 * h, off), (1.6 * h, off)] if i % 2 == 0 else [(1.6 * h, off), (-1.6 * h, off)]
            for x, y in ends:
                xr = x * math.cos(a) - y * math.sin(a)
                yr = x * math.sin(a) + y * math.cos(a)
                pts.append((centre[0] + max(-h, min(h, xr)), centre[1] + max(-h, min(h, yr))))
        pen.line(pts, hatch, wobble=0.06)


def circle(pen: Pen, centre, box: float, ink) -> None:
    rng = pen.rng
    r = box / 2 + rng.uniform(1.0, 1.5)
    start = rng.uniform(0, 2 * math.pi)
    pts = []
    for i in range(48):
        t = start + i / 44 * 2 * math.pi  # a little more than a full turn, as drawn by hand
        rr = r * (1 + 0.06 * math.sin(3 * t + start))
        pts.append((centre[0] + rr * math.cos(t) * 1.08, centre[1] + rr * math.sin(t)))
    pen.line(pts, ink, wobble=0.04)


def erased(pen: Pen, centre, box: float) -> None:
    """What stays of a pencil cross after rubbing it out: a pale ghost and a smudge."""
    cross(pen, centre, box, ERASED)
    rng = pen.rng
    for _ in range(3):
        y = centre[1] + rng.normal(0, 0.6)
        pen.stroke((centre[0] - 1.8, y), (centre[0] + 1.8, y + rng.normal(0, 0.3)), ((0.9, 0.9, 0.91), 0.9, 0.35))


def fill_page(page: pymupdf.Page, booklet: str, rng: np.random.Generator) -> None:
    layout = build_layout()
    box = layout.params.box_size
    pen = Pen(page, rng)
    ink = BALLPOINT.get(booklet, BALLPOINT["001"])
    centre_of = {b.id: layout.to_page(b.x, b.y) for b in layout.boxes}

    for task, style in zip(PLAN, STYLES, strict=True):
        for box_id, states in task.expected.items():
            c = centre_of[box_id]
            if style in ("cross", "correction") and TICKED in states:
                cross(pen, c, box, ink)
            elif style in ("filled", "correction") and DOUBTFUL in states:
                blacken(pen, c, box, ink)
            elif style == "tick":
                tick(pen, c, box, ink)
            elif style == "small":
                cross(pen, c, box, ink, scale=0.42)
            elif style == "large":
                cross(pen, c, box, ink, scale=1.7)
            elif style == "half":
                half_stroke(pen, c, box, ink)
            elif style == "faint":
                cross(pen, c, box, FAINT_PENCIL)
            elif style == "pencil":
                cross(pen, c, box, PENCIL)
            elif style == "erased":
                erased(pen, c, box)
            elif style == "circle":
                circle(pen, c, box, ink)
            elif style == "felt":
                cross(pen, c, box, FELT)

    # The student number: written into the fields above the grid and ticked below them.
    number = STUDENT_NUMBERS[booklet]
    p = layout.params
    font = {"fontfile": str(HANDWRITING_FONT), "fontname": "hand"} if HANDWRITING_FONT.exists() else {"fontname": "helv"}
    for pos, digit in enumerate(number):
        left = p.student_left - 0.5 + pos * p.student_col_pitch
        x = (left + 1.1 + rng.normal(0, 0.25)) * MM
        y = (36.0 + rng.normal(0, 0.3)) * MM
        page.insert_text((x, y), digit, fontsize=rng.uniform(15, 17), color=ink[0],
                         morph=(pymupdf.Point(x, y), pymupdf.Matrix(rng.normal(0, 4))), **font)
    for b in layout.boxes:
        if b.kind == "student" and str(b.digit) == number[b.digit_position]:
            cross(pen, centre_of[b.id], box, ink)


def cmd_fill(sheets: Path, out: Path, seed: int) -> None:
    rng = np.random.default_rng(seed)
    with pymupdf.open(sheets) as doc:
        for index, page in enumerate(doc):
            fill_page(page, sorted(STUDENT_NUMBERS)[index], rng)
        doc.save(out, garbage=3, deflate=True)
    print(f"Ausgefüllt: {out}")


def cmd_simulate(filled: Path, out: Path, seed: int) -> None:
    rng = np.random.default_rng(seed)
    result = pymupdf.open()
    booklets = sorted(STUDENT_NUMBERS)
    with pymupdf.open(filled) as doc:
        for index, page in enumerate(doc):
            pix = page.get_pixmap(dpi=300, colorspace=pymupdf.csGRAY, alpha=False)
            img = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.stride)[:, : pix.w].astype(np.float32)
            h, w = img.shape
            # Toner is never fully black and paper never fully white.
            img = 18 + img * (226 - 18) / 255
            # The sheet lies a little turned and shifted on the glass.
            m = cv2.getRotationMatrix2D((w / 2, h / 2), rng.uniform(-1.2, 1.2), rng.uniform(0.985, 1.0))
            m[:, 2] += rng.uniform(-25, 25, 2)
            img = cv2.warpAffine(img, m, (w, h), borderValue=226)
            img = cv2.GaussianBlur(img, (0, 0), 0.9)
            img += rng.normal(0, 3.5, img.shape)
            img = np.clip(img, 0, 255).astype(np.uint8)
            if booklets[index] == UPSIDE_DOWN_BOOKLET:
                img = cv2.rotate(img, cv2.ROTATE_180)
            ok, data = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
            target = result.new_page(width=page.rect.width, height=page.rect.height)
            target.insert_image(target.rect, stream=data.tobytes())
    result.save(out)
    print(f"Simulierter Scan: {out}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fill the scan test sheets by machine")
    sub = parser.add_subparsers(dest="command", required=True)
    fill = sub.add_parser("fill", help="draw handwritten-looking marks into the test sheets")
    fill.add_argument("sheets", type=Path)
    fill.add_argument("out", type=Path)
    fill.add_argument("--seed", type=int, default=7)
    sim = sub.add_parser("simulate", help="turn filled sheets into a copier-like scan")
    sim.add_argument("filled", type=Path)
    sim.add_argument("out", type=Path)
    sim.add_argument("--seed", type=int, default=11)
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.command == "fill":
        cmd_fill(args.sheets, args.out, args.seed)
    else:
        cmd_simulate(args.filled, args.out, args.seed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
