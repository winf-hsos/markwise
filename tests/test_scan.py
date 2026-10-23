"""Synthetic end-to-end tests for the answer sheet and the scan reader.

The answer sheet is generated, rendered at 300 dpi, ticked programmatically
with OpenCV (crosses, ticks, filled boxes, light half ticks, empty rows),
distorted like a copier scan (rotation, scaling, shift, blur, noise, JPEG),
written back to a PDF and read. All data is invented.
"""

from __future__ import annotations

import json

import cv2
import numpy as np
import pymupdf
import pytest

from markwise.scan import (
    DOUBTFUL,
    EMPTY,
    REASON_FAINT,
    REASON_FILLED,
    REASON_HEAVY,
    REASON_PARTIAL,
    TICKED,
    Thresholds,
    classify,
    crop_box,
    debug_image,
    looks_like_cross,
    read_page_image,
    read_pdf,
)
from markwise.sheet import Layout, SheetPage, build_layout, encode_payload, parse_payload, render_sheet_pdf
from markwise.sheet.layout import BoxSpec

DPI = 300
PX_PER_MM = DPI / 25.4
A4_PT = (595.28, 841.89)

# What is drawn into which box: box id -> kind of mark.
MARKS: dict[str, str] = {
    "q1a": "cross",
    "q2b": "cross",
    "q3c": "cross",
    "q4d": "cross",
    "q5e": "cross",
    "q6a": "cross",
    "q6c": "cross",
    "q7b": "tick",
    "q8d": "fill",
    "q9a": "fill",
    "q9b": "cross",
    "q10c": "light_half",
    "q11e": "dark_half",
    # q12: deliberately empty row
    "q13c": "big_cross",
    "q14b": "pencil_cross",
    "q15d": "felt_cross",
    "q21a": "cross",
    "q30e": "cross",
    "q35b": "tick",
    "q40c": "cross",
}

# Expected state and acceptable reasons per kind of mark.
EXPECTED = {
    "cross": (TICKED, {None}),
    "big_cross": (TICKED, {None}),
    "pencil_cross": (TICKED, {None}),
    "felt_cross": (TICKED, {None}),
    "tick": (TICKED, {None}),
    "fill": (DOUBTFUL, {REASON_FILLED}),
    "light_half": (DOUBTFUL, {REASON_FAINT, REASON_PARTIAL}),
    "dark_half": (DOUBTFUL, {REASON_PARTIAL}),
}

STUDENT_NUMBERS = {"001": "4711083", "002": "1234567", "003": "9050210"}


# ---------------------------------------------------------------------------
# Drawing helpers (page raster at 300 dpi)


def _centre_px(layout: Layout, box: BoxSpec) -> tuple[float, float]:
    x, y = layout.to_page(box.x, box.y)
    return x * PX_PER_MM, y * PX_PER_MM


def _pt(x: float, y: float) -> tuple[int, int]:
    return int(round(x)), int(round(y))


def draw_mark(img: np.ndarray, layout: Layout, box: BoxSpec, kind: str) -> None:
    cx, cy = _centre_px(layout, box)
    h = box.size / 2 * PX_PER_MM
    ink, pen = 35, 4  # ballpoint: dark grey, about 0.35 mm wide
    if kind in ("cross", "big_cross", "pencil_cross"):
        k = {"cross": 0.8, "big_cross": 1.35, "pencil_cross": 0.8}[kind]
        colour = 95 if kind == "pencil_cross" else ink
        # Slightly asymmetric, as drawn by hand.
        cv2.line(img, _pt(cx - k * h, cy - k * h * 0.9), _pt(cx + k * h, cy + k * h), colour, pen, cv2.LINE_AA)
        cv2.line(img, _pt(cx + k * h * 0.95, cy - k * h), _pt(cx - k * h, cy + k * h * 0.9), colour, pen, cv2.LINE_AA)
    elif kind == "felt_cross":  # thick felt pen: lots of ink, but still a cross
        k = 0.85 * h
        cv2.line(img, _pt(cx - k, cy - k), _pt(cx + k, cy + k), 20, 10, cv2.LINE_AA)
        cv2.line(img, _pt(cx + k, cy - k), _pt(cx - k, cy + k), 20, 10, cv2.LINE_AA)
    elif kind == "tick":
        pts = np.array([_pt(cx - 0.7 * h, cy), _pt(cx - 0.15 * h, cy + 0.65 * h), _pt(cx + 0.85 * h, cy - 0.85 * h)])
        cv2.polylines(img, [pts], False, ink, pen, cv2.LINE_AA)
    elif kind == "fill":
        cv2.rectangle(img, _pt(cx - 0.92 * h, cy - 0.92 * h), _pt(cx + 0.92 * h, cy + 0.92 * h), 45, -1)
    elif kind == "light_half":
        cv2.line(img, _pt(cx - 0.6 * h, cy + 0.05 * h), _pt(cx - 0.05 * h, cy + 0.6 * h), 175, 4, cv2.LINE_AA)
    elif kind == "dark_half":
        cv2.line(img, _pt(cx - 0.55 * h, cy + 0.05 * h), _pt(cx - 0.15 * h, cy + 0.45 * h), ink, pen, cv2.LINE_AA)
    else:
        raise ValueError(kind)


def fill_page(img: np.ndarray, layout: Layout, student_number: str) -> None:
    boxes = {b.id: b for b in layout.boxes}
    for box_id, kind in MARKS.items():
        draw_mark(img, layout, boxes[box_id], kind)
    for pos, digit in enumerate(student_number):
        draw_mark(img, layout, boxes[f"s{pos + 1}-{digit}"], "cross")


def blank_out(img: np.ndarray, layout: Layout, x: float, y: float, w: float, h: float) -> None:
    """Paint a page region (mark system, mm) white, e.g. to remove the QR code."""
    px, py = layout.to_page(x, y)
    cv2.rectangle(
        img, _pt(px * PX_PER_MM, py * PX_PER_MM), _pt((px + w) * PX_PER_MM, (py + h) * PX_PER_MM), 255, -1
    )


def copier(
    img: np.ndarray,
    angle: float,
    scale: float,
    shift: tuple[float, float],
    seed: int,
    stretch: float = 1.0,
    wave_mm: float = 0.0,
) -> np.ndarray:
    """Distort a clean page raster like a copier scan.

    ``stretch`` scales the feed direction differently from the other one;
    ``wave_mm`` adds a smooth, non-linear displacement as from wavy paper,
    which the corner marks alone cannot correct.
    """
    h, w = img.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, scale)
    m[1, :] *= stretch
    m[:, 2] += shift
    out = cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_LINEAR, borderValue=255)
    if wave_mm:
        ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
        a = wave_mm * PX_PER_MM
        map_x = xs + a * np.sin(2 * np.pi * ys / (h * 0.7))
        map_y = ys + a * np.sin(2 * np.pi * xs / (w * 0.6))
        out = cv2.remap(out, map_x, map_y, cv2.INTER_LINEAR, borderValue=255)
    out = cv2.GaussianBlur(out, (3, 3), 0).astype(np.float32)
    out = out * 0.86 + 22  # greyish paper, not quite black toner
    rng = np.random.default_rng(seed)
    out += rng.normal(0, 7, out.shape)
    return np.clip(out, 0, 255).astype(np.uint8)


def write_scan_pdf(images: list[np.ndarray], path) -> None:
    doc = pymupdf.open()
    for img in images:
        ok, jpg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        assert ok
        page = doc.new_page(width=A4_PT[0], height=A4_PT[1])
        page.insert_image(page.rect, stream=jpg.tobytes())
    doc.save(path)
    doc.close()


def render_pages(pdf: bytes) -> list[np.ndarray]:
    pages = []
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY, alpha=False)
            pages.append(np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.stride)[:, : pix.w].copy())
    return pages


# ---------------------------------------------------------------------------
# Fixtures


@pytest.fixture(scope="module")
def layout() -> Layout:
    return build_layout()


@pytest.fixture(scope="module")
def scan(tmp_path_factory, layout):
    """Three filled sheets: upright, upside down, and one without QR and one mark."""
    tmp = tmp_path_factory.mktemp("scan")
    pages = [SheetPage(exam="TEST", booklet=bk, title="Markwise · Testbogen") for bk in STUDENT_NUMBERS]
    sheet_pdf = render_sheet_pdf(pages, tmp / "sheet.pdf", layout)
    clean = render_pages(sheet_pdf)
    scanned = []
    for img, bk in zip(clean, STUDENT_NUMBERS):
        fill_page(img, layout, STUDENT_NUMBERS[bk])
    # Page 3: QR code and bottom-right corner mark missing.
    q = layout.qr
    blank_out(clean[2], layout, q.x - 1, q.y - 1, q.width + 2, q.height + 2)
    s = layout.params.mark_size
    blank_out(clean[2], layout, layout.width - s, layout.height - s, 2 * s, 2 * s)

    scanned.append(copier(clean[0], angle=2.5, scale=0.97, shift=(18, -25), seed=1, stretch=1.012, wave_mm=0.8))
    scanned.append(copier(clean[1], angle=181.8, scale=1.015, shift=(-12, 20), seed=2))
    scanned.append(copier(clean[2], angle=-2.0, scale=0.985, shift=(5, 10), seed=3))
    path = tmp / "scan.pdf"
    write_scan_pdf(scanned, path)
    return read_pdf(path, layout, keep_images=True)


# ---------------------------------------------------------------------------
# Tests


def test_payload_round_trip():
    text = encode_payload("TEST", 0, 1, "001")
    assert text == "MW1;exam=TEST;var=0;page=1;bk=001"
    assert parse_payload(text) == {"format": "MW1", "exam": "TEST", "var": "0", "page": "1", "bk": "001"}
    assert parse_payload("something else") is None


def test_layout_json_round_trip(layout, tmp_path):
    path = tmp_path / "layout.json"
    layout.to_json(path)
    again = Layout.from_json(path)
    assert again == layout
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["boxes"]) == 40 * 5 + 7 * 10
    # Corner mark centres define the frame: everything scanned lies inside it.
    for b in layout.boxes:
        assert 0 < b.x < layout.width and 0 < b.y < layout.height


def test_classify_thresholds():
    t = Thresholds()
    assert classify(0.0, 0.0, t) == (EMPTY, None)
    assert classify(0.3, 0.4, t) == (TICKED, None)
    assert classify(0.95, 0.97, t) == (DOUBTFUL, REASON_FILLED)
    assert classify(0.0, 0.1, t) == (DOUBTFUL, REASON_FAINT)
    assert classify(0.05, 0.08, t) == (DOUBTFUL, REASON_PARTIAL)
    assert classify(0.65, 0.75, t) == (DOUBTFUL, REASON_HEAVY)
    assert classify(0.65, 0.75, t, cross=True) == (TICKED, None)


def test_cross_shape():
    n = 37
    filled = np.ones((n, n), bool)
    cross = np.zeros((n, n), bool)
    for i in range(n):
        cross[i, max(i - 5, 0) : i + 6] = True
        cross[i, max(n - 1 - i - 5, 0) : n - i + 5] = True
    assert looks_like_cross(cross)
    assert not looks_like_cross(filled)


def test_pages_identified(scan):
    assert len(scan.pages) == 3
    p1, p2, p3 = scan.pages
    assert p1.qr["bk"] == "001" and not p1.upside_down
    assert p2.qr["bk"] == "002" and p2.upside_down
    assert p1.qr_text == "MW1;exam=TEST;var=0;page=1;bk=001"
    codes3 = {p.code for p in p3.problems}
    assert "qr_unreadable" in codes3
    assert "corner_mark_estimated" in codes3
    assert p3.qr is None and p3.boxes


@pytest.mark.parametrize("index", [0, 1, 2])
def test_student_number(scan, index):
    bk = list(STUDENT_NUMBERS)[index]
    assert scan.pages[index].student_number == STUDENT_NUMBERS[bk]


@pytest.mark.parametrize("index", [0, 1, 2])
def test_boxes(scan, layout, index):
    page = scan.pages[index]
    wrong = []
    for b in page.boxes:
        if b.kind != "answer":
            continue
        state, reasons = EXPECTED[MARKS[b.id]] if b.id in MARKS else (EMPTY, {None})
        if b.state != state or b.reason not in reasons:
            wrong.append(f"{b.id}: {b.state}/{b.reason} fill={b.fill_ratio} faint={b.faint_ratio}")
    assert not wrong, "\n".join(wrong)


def test_answers_and_doubtful(scan):
    page = scan.pages[0]
    answers = page.answers()
    assert answers[1] == ["a"]
    assert answers[6] == ["a", "c"]
    assert answers[9] == ["b"]  # a is filled, hence doubtful and not counted
    assert answers[12] == []
    assert {b.id for b in page.doubtful()} == {"q8d", "q9a", "q10c", "q11e"}


def test_debug_outputs(scan, layout):
    page = scan.pages[1]
    img = debug_image(page, layout)
    assert img.ndim == 3 and img.shape[:2] == page.image.shape
    crop = crop_box(page, page.box("q8d"), layout.params.box_size)
    assert crop.size > 0 and crop.mean() < 200  # the filled box is dark
    json.dumps(scan.to_dict())  # results serialise


def test_blank_page_reports_missing_marks(layout):
    blank = np.full((3508, 2480), 245, np.uint8)
    page = read_page_image(blank, layout)
    assert [p.code for p in page.problems] == ["no_corner_marks"]
    assert page.boxes == []
