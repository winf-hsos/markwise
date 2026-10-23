"""Images for checking a reading by eye: box crops and an annotated page."""

from __future__ import annotations

import cv2
import numpy as np

from ..sheet.layout import Layout
from .model import DOUBTFUL, EMPTY, TICKED, BoxReading, PageResult

# BGR colours per state.
COLOURS = {EMPTY: (170, 170, 170), TICKED: (40, 160, 40), DOUBTFUL: (0, 140, 255)}


def _px(page: PageResult, x_mm: float, y_mm: float) -> tuple[int, int]:
    ppm, margin = page.pixels_per_mm, page.margin_mm
    return int(round((x_mm + margin) * ppm)), int(round((y_mm + margin) * ppm))


def crop_box(page: PageResult, box: BoxReading, size_mm: float, margin_mm: float = 2.5) -> np.ndarray:
    """A greyscale crop around a box, from the straightened page image."""
    if page.image is None:
        raise ValueError("page was read without keep_image=True")
    half = size_mm / 2 + margin_mm
    x0, y0 = _px(page, box.x - half, box.y - half)
    x1, y1 = _px(page, box.x + half, box.y + half)
    h, w = page.image.shape
    return page.image[max(y0, 0) : min(y1, h), max(x0, 0) : min(x1, w)].copy()


def debug_image(page: PageResult, layout: Layout) -> np.ndarray:
    """The straightened page with every box outlined in the colour of its state."""
    if page.image is None:
        raise ValueError("page was read without keep_image=True")
    img = cv2.cvtColor(page.image, cv2.COLOR_GRAY2BGR)
    sizes = {b.id: b.size for b in layout.boxes}
    for b in page.boxes:
        half = sizes[b.id] / 2 + 0.4
        p0 = _px(page, b.x - half, b.y - half)
        p1 = _px(page, b.x + half, b.y + half)
        colour = COLOURS[b.state]
        cv2.rectangle(img, p0, p1, colour, 3 if b.state != EMPTY else 1)
        if b.state != EMPTY:
            label = f"{b.fill_ratio:.2f}" + (f" {b.reason}" if b.reason else "")
            cv2.putText(img, label, (p0[0], p1[1] + 14), cv2.FONT_HERSHEY_SIMPLEX, 0.55, colour, 1, cv2.LINE_AA)
    qr = layout.qr
    cv2.rectangle(img, _px(page, qr.x, qr.y), _px(page, qr.x + qr.width, qr.y + qr.height), (200, 80, 0), 2)
    for mx, my in layout.mark_centres:
        cv2.drawMarker(img, _px(page, mx, my), (0, 0, 255), cv2.MARKER_CROSS, 40, 2)
    status = f"QR: {page.qr_text or 'nicht gelesen'}" + ("  (Seite stand auf dem Kopf)" if page.upside_down else "")
    cv2.putText(img, status, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 80, 0), 2, cv2.LINE_AA)
    return img
