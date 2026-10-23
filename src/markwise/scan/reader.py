"""Read scanned answer sheets.

Pipeline per page:

1. Render the PDF page at 300 dpi as greyscale (PyMuPDF).
2. Find the four corner marks and warp the page onto a canvas in the layout's
   mark system (a fixed number of pixels per millimetre, with a margin).
3. Decide the orientation: the QR code sits top right and the region opposite
   to it is blank, so an upside-down page shows its dark QR area where the
   blank region should be. Such pages are turned by 180 degrees.
4. Decode the QR code.
5. For every tick box, refine its position locally (the printed outline is
   searched up to two millimetres around its place, smoothed over the
   neighbouring boxes), then measure the ink in the inner area, which
   excludes the outline, and classify the box.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pymupdf

from ..sheet.layout import BoxSpec, Layout, Rect, build_layout
from ..sheet.qr import parse_payload
from .corners import find_corner_marks
from .model import (
    DOUBTFUL,
    EMPTY,
    REASON_FAINT,
    REASON_FILLED,
    REASON_HEAVY,
    REASON_PARTIAL,
    TICKED,
    BoxReading,
    PageResult,
    Problem,
    ScanResult,
)

RENDER_DPI = 300
CANVAS_PX_PER_MM = 12.0
CANVAS_MARGIN_MM = 12.0


@dataclass(frozen=True)
class Thresholds:
    """Numbers that decide how a box is classified; tuned on synthetic sheets.

    ``fill_ratio`` is the share of inner-area pixels darker than ``ink``;
    ``faint_ratio`` the share darker than ``faint``. Darkness is normalised per
    page: 0 is the paper, 1 the ink of the corner marks.
    """

    ink: float = 0.45
    faint: float = 0.15
    inner_inset_mm: float = 0.7  # from the outer box edge to the measured area
    empty_fill: float = 0.02  # at most this much ink ...
    empty_faint: float = 0.04  # ... and this much visible mark: empty
    tick_fill: float = 0.08  # from here on: a clear tick or cross
    heavy_fill: float = 0.55  # from here on: doubtful, more than a cross
    filled_fill: float = 0.80  # from here on: doubtful, box blackened
    search_mm: float = 2.0  # wide search for a box outline around its place
    local_search_mm: float = 0.35  # narrow search around the neighbours' shift
    neighbourhood_mm: float = 20.0  # radius of the neighbours pooled for that shift
    outline_score: float = 0.1  # minimum contrast of a printed outline that counts
    qr_contrast: float = 0.12  # minimum darkness difference to tell orientation


# ---------------------------------------------------------------------------
# Page images


def pdf_page_images(path: str | Path, dpi: int = RENDER_DPI):
    """Yield every page of a PDF as a greyscale uint8 array."""
    with pymupdf.open(path) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY, alpha=False)
            img = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.stride)[:, : pix.w]
            yield img.copy()


def _canvas_size(layout: Layout) -> tuple[int, int]:
    w = (layout.width + 2 * CANVAS_MARGIN_MM) * CANVAS_PX_PER_MM
    h = (layout.height + 2 * CANVAS_MARGIN_MM) * CANVAS_PX_PER_MM
    return int(round(w)), int(round(h))


def _to_canvas(x_mm: float, y_mm: float) -> tuple[float, float]:
    """Mark system (mm) to canvas pixels."""
    return (x_mm + CANVAS_MARGIN_MM) * CANVAS_PX_PER_MM, (y_mm + CANVAS_MARGIN_MM) * CANVAS_PX_PER_MM


def _rect_px(rect: Rect) -> tuple[int, int, int, int]:
    x0, y0 = _to_canvas(rect.x, rect.y)
    x1, y1 = _to_canvas(rect.x + rect.width, rect.y + rect.height)
    return int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))


def _darkness_map(canvas: np.ndarray, layout: Layout) -> tuple[np.ndarray, float, float]:
    """Normalise the canvas to darkness 0 (paper) .. 1 (mark ink)."""
    x0, y0 = _to_canvas(0, 0)
    x1, y1 = _to_canvas(layout.width, layout.height)
    inner = canvas[int(y0) : int(y1), int(x0) : int(x1)]
    white = float(np.percentile(inner, 90))
    r = 1.5 * CANVAS_PX_PER_MM
    samples = []
    for mx, my in layout.mark_centres:
        cx, cy = _to_canvas(mx, my)
        samples.append(canvas[int(cy - r) : int(cy + r), int(cx - r) : int(cx + r)].ravel())
    black = float(np.median(np.concatenate(samples)))
    span = max(white - black, 1.0)
    dark = np.clip((white - canvas.astype(np.float32)) / span, 0.0, 1.0)
    dark = cv2.blur(dark, (3, 3))
    return dark, white, black


def _mean_in(dark: np.ndarray, rect: Rect) -> float:
    x0, y0, x1, y1 = _rect_px(rect)
    region = dark[max(y0, 0) : max(y1, 0), max(x0, 0) : max(x1, 0)]
    return float(region.mean()) if region.size else 0.0


# ---------------------------------------------------------------------------
# QR code


def _decode_qr(canvas: np.ndarray, rect: Rect) -> str | None:
    """Try to decode the QR code in its expected region, with a few fallbacks."""
    pad = 4.0
    x0, y0, x1, y1 = _rect_px(Rect(rect.x - pad, rect.y - pad, rect.width + 2 * pad, rect.height + 2 * pad))
    h, w = canvas.shape
    crop = canvas[max(y0, 0) : min(y1, h), max(x0, 0) : min(x1, w)]
    if crop.size == 0:
        return None
    detector = cv2.QRCodeDetector()
    _, otsu = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    attempts = [
        crop,
        otsu,
        cv2.resize(otsu, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA),
        cv2.GaussianBlur(crop, (5, 5), 0),
    ]
    for img in attempts:
        try:
            text, points, _ = detector.detectAndDecode(img)
        except cv2.error:
            continue
        if text:
            return text
    return None


# ---------------------------------------------------------------------------
# Tick boxes


def _square_sums(integral: np.ndarray, cx: int, cy: int, half: int, r: int) -> np.ndarray:
    """Sum of a (2*half)^2 square centred at (cx+dx, cy+dy) for all |dx|,|dy| <= r."""
    y0, y1, x0, x1 = cy - half, cy + half, cx - half, cx + half
    s = slice
    return (
        integral[s(y1 - r, y1 + r + 1), s(x1 - r, x1 + r + 1)]
        - integral[s(y0 - r, y0 + r + 1), s(x1 - r, x1 + r + 1)]
        - integral[s(y1 - r, y1 + r + 1), s(x0 - r, x0 + r + 1)]
        + integral[s(y0 - r, y0 + r + 1), s(x0 - r, x0 + r + 1)]
    )


def _outline_scores(integral: np.ndarray, box: BoxSpec, r: int) -> np.ndarray:
    """Outline score for every shift (dx, dy) with |dx|, |dy| <= r pixels.

    The score is the darkness of a thin band on the printed outline minus the
    darkness of the band just outside it, so a blackened box still peaks at
    its true place. Index ``[r + dy, r + dx]`` holds the score of that shift.
    """
    ppm = CANVAS_PX_PER_MM
    cx, cy = (int(round(v)) for v in _to_canvas(box.x, box.y))
    half = box.size / 2
    a_in, a_out, a_sur = (int(round(v * ppm)) for v in (half - 0.3, half + 0.3, half + 1.0))
    s_in = _square_sums(integral, cx, cy, a_in, r)
    s_out = _square_sums(integral, cx, cy, a_out, r)
    s_sur = _square_sums(integral, cx, cy, a_sur, r)
    frame = (s_out - s_in) / ((2 * a_out) ** 2 - (2 * a_in) ** 2)
    surround = (s_sur - s_out) / ((2 * a_sur) ** 2 - (2 * a_out) ** 2)
    return frame - surround


def looks_like_cross(ink: np.ndarray) -> bool:
    """Whether a heavily inked inner area is a thick cross rather than a filled box.

    A cross, however thick, leaves the middles of the four edges blank and
    covers the centre; a blackened box covers both.
    """
    n = min(ink.shape)
    if n < 8:
        return False
    depth = max(int(round(n * 0.25)), 2)  # how far a zone reaches in from the edge
    lo, hi = n // 2 - max(int(round(n * 0.12)), 1), n // 2 + max(int(round(n * 0.12)), 1)
    edges = [ink[:depth, lo:hi], ink[-depth:, lo:hi], ink[lo:hi, :depth], ink[lo:hi, -depth:]]
    centre = ink[lo:hi, lo:hi]
    edge_ink = sum(float(e.mean()) for e in edges) / 4
    return edge_ink < 0.4 and float(centre.mean()) > 0.6


def classify(fill: float, faint: float, t: Thresholds, cross: bool = False) -> tuple[str, str | None]:
    """Turn the measured ink of a box into a state and, if doubtful, a reason.

    ``cross`` says whether the ink has the shape of a cross (see
    :func:`looks_like_cross`); a thick cross is a tick, not a correction.
    """
    if fill >= t.heavy_fill and cross:
        return TICKED, None
    if fill >= t.filled_fill:
        return DOUBTFUL, REASON_FILLED
    if fill >= t.heavy_fill:
        return DOUBTFUL, REASON_HEAVY
    if fill >= t.tick_fill:
        return TICKED, None
    if fill <= t.empty_fill and faint <= t.empty_faint:
        return EMPTY, None
    if fill > t.empty_fill:
        return DOUBTFUL, REASON_PARTIAL
    return DOUBTFUL, REASON_FAINT


def _read_boxes(dark: np.ndarray, layout: Layout, t: Thresholds) -> list[BoxReading]:
    ppm = CANVAS_PX_PER_MM
    integral = cv2.integral(dark, sdepth=cv2.CV_64F)

    # Local alignment in two stages. Paper is never perfectly flat, so after
    # the warp a box can still be off by a millimetre or so. First every box
    # searches its outline in a wide window; the shifts of its neighbours are
    # then pooled into a smooth local estimate, and the box takes the best
    # outline within a narrow window around that estimate. A single box whose
    # outline is hidden (e.g. under a big scribble) thus follows its neighbours.
    r_wide = int(round(t.search_mm * ppm))
    r_narrow = int(round(t.local_search_mm * ppm))
    boxes = layout.boxes
    maps = [_outline_scores(integral, box, r_wide) for box in boxes]
    best = np.array([np.unravel_index(int(np.argmax(m)), m.shape) for m in maps], dtype=float) - r_wide
    good = np.array([m.max() > t.outline_score for m in maps])
    centres = np.array([(b.x, b.y) for b in boxes])
    dist = np.hypot(*(centres[:, None, :] - centres[None, :, :]).transpose(2, 0, 1))
    fallback = np.median(best[good], axis=0) if good.any() else np.zeros(2)

    shifts: list[tuple[float, float]] = []
    for i, m in enumerate(maps):
        near = good & (dist[i] <= t.neighbourhood_mm)
        ly, lx = np.median(best[near], axis=0) if near.sum() >= 3 else fallback
        # Narrow window around the local estimate, clipped to the score map.
        cy, cx = int(round(ly)) + r_wide, int(round(lx)) + r_wide
        y0, y1 = max(cy - r_narrow, 0), min(cy + r_narrow + 1, m.shape[0])
        x0, x1 = max(cx - r_narrow, 0), min(cx + r_narrow + 1, m.shape[1])
        window = m[y0:y1, x0:x1]
        if window.size and window.max() > t.outline_score:
            iy, ix = np.unravel_index(int(np.argmax(window)), window.shape)
            shifts.append((float(x0 + ix - r_wide), float(y0 + iy - r_wide)))
        else:
            shifts.append((float(lx), float(ly)))

    readings: list[BoxReading] = []
    for box, (dx, dy) in zip(boxes, shifts):
        box_half = box.size / 2
        inner_half = (box_half - t.inner_inset_mm) * ppm
        cx, cy = _to_canvas(box.x, box.y)
        cx, cy = cx + dx, cy + dy
        x0, x1 = int(round(cx - inner_half)), int(round(cx + inner_half))
        y0, y1 = int(round(cy - inner_half)), int(round(cy + inner_half))
        region = dark[y0:y1, x0:x1]
        ink = region > t.ink
        fill = float(ink.mean())
        faint = float((region > t.faint).mean())
        cross = fill >= t.heavy_fill and looks_like_cross(ink)
        state, reason = classify(fill, faint, t, cross)
        readings.append(
            BoxReading(
                id=box.id,
                kind=box.kind,
                state=state,
                fill_ratio=round(fill, 4),
                faint_ratio=round(faint, 4),
                darkness=round(float(region.mean()), 4),
                reason=reason,
                question=box.question,
                option=box.option,
                digit_position=box.digit_position,
                digit=box.digit,
                x=round(box.x + dx / ppm, 3),
                y=round(box.y + dy / ppm, 3),
                shift=(round(dx / ppm, 3), round(dy / ppm, 3)),
            )
        )
    return readings


def _student_number(readings: list[BoxReading], layout: Layout, problems: list[Problem]) -> str | None:
    digits = layout.params.student_digits
    columns: dict[int, list[BoxReading]] = defaultdict(list)
    for b in readings:
        if b.kind == "student":
            columns[b.digit_position].append(b)
    if not columns:
        return None
    if all(b.state == EMPTY for col in columns.values() for b in col):
        problems.append(Problem("student_number_empty", "Keine Matrikelnummer angekreuzt."))
        return None
    result, unclear = [], []
    for pos in range(digits):
        col = columns[pos]
        ticked = [b.digit for b in col if b.state == TICKED]
        doubtful = [b for b in col if b.state == DOUBTFUL]
        if len(ticked) == 1 and not doubtful:
            result.append(str(ticked[0]))
        else:
            result.append("?")
            unclear.append(pos + 1)
    if unclear:
        where = ", ".join(str(p) for p in unclear)
        problems.append(
            Problem("student_number_unclear", f"Matrikelnummer an Stelle {where} nicht eindeutig.")
        )
    return "".join(result)


# ---------------------------------------------------------------------------
# Public entry points


def read_page_image(
    gray: np.ndarray,
    layout: Layout | None = None,
    page_index: int = 0,
    thresholds: Thresholds | None = None,
    dpi: float = RENDER_DPI,
    keep_image: bool = False,
) -> PageResult:
    """Read one page given as a greyscale image rendered at ``dpi``."""
    layout = layout or build_layout()
    t = thresholds or Thresholds()
    page = PageResult(page_index=page_index, pixels_per_mm=CANVAS_PX_PER_MM, margin_mm=CANVAS_MARGIN_MM)

    if gray.shape[1] > gray.shape[0]:
        gray = cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE)  # landscape scan of a portrait sheet

    corners, problems = find_corner_marks(gray, dpi / 25.4, layout)
    page.problems.extend(problems)
    if corners is None:
        return page

    # Warp onto the canvas of the mark system.
    src = corners.astype(np.float32)
    dst = np.array([_to_canvas(x, y) for x, y in layout.mark_centres], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(src, dst)
    canvas = cv2.warpPerspective(gray, matrix, _canvas_size(layout), flags=cv2.INTER_LINEAR, borderValue=255)
    dark, white, black = _darkness_map(canvas, layout)
    page.white_level, page.black_level = round(white, 1), round(black, 1)
    if white - black < 60:
        page.problems.append(Problem("low_contrast", "Sehr geringer Kontrast zwischen Papier und Tinte."))

    # Orientation from the QR region versus the blank region opposite to it.
    qr_rect = layout.qr
    opposite = qr_rect.rotated_180(layout.width, layout.height)
    qr_dark, opp_dark = _mean_in(dark, qr_rect), _mean_in(dark, opposite)
    flip = opp_dark - qr_dark > t.qr_contrast
    orientation_known = abs(opp_dark - qr_dark) > t.qr_contrast

    def turn(c: np.ndarray, d: np.ndarray, cs: np.ndarray):
        return cv2.rotate(c, cv2.ROTATE_180), cv2.rotate(d, cv2.ROTATE_180), cs[[2, 3, 0, 1]]

    if flip:
        canvas, dark, corners = turn(canvas, dark, corners)
    text = _decode_qr(canvas, qr_rect)
    if text is None and not orientation_known:
        # The darkness test was undecided: try the other way round.
        c2, d2, k2 = turn(canvas, dark, corners)
        text = _decode_qr(c2, qr_rect)
        if text is not None:
            canvas, dark, corners, flip = c2, d2, k2, not flip
    page.upside_down = flip
    page.corners_px = [(round(float(x), 1), round(float(y), 1)) for x, y in corners]

    if text is None:
        page.problems.append(Problem("qr_unreadable", "QR-Code nicht lesbar; die Seite ist nicht zugeordnet."))
        if not orientation_known:
            page.problems.append(
                Problem("orientation_unknown", "Lage der Seite unklar; sie wurde als aufrecht angenommen.")
            )
    else:
        page.qr_text = text
        page.qr = parse_payload(text)
        if page.qr is None:
            page.problems.append(Problem("qr_foreign", f"QR-Code gehört nicht zu Markwise: {text!r}"))

    page.boxes = _read_boxes(dark, layout, t)
    page.student_number = _student_number(page.boxes, layout, page.problems)
    if keep_image:
        page.image = canvas
    return page


def read_pdf(
    path: str | Path,
    layout: Layout | None = None,
    thresholds: Thresholds | None = None,
    keep_images: bool = False,
) -> ScanResult:
    """Read every page of a scanned PDF."""
    layout = layout or build_layout()
    result = ScanResult(source=str(path))
    for index, gray in enumerate(pdf_page_images(path)):
        result.pages.append(
            read_page_image(gray, layout, index, thresholds, RENDER_DPI, keep_image=keep_images)
        )
    return result
