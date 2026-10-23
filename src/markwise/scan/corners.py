"""Find the four solid corner marks on a scanned page."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from ..sheet.layout import Layout
from .model import Problem

CORNER_NAMES_DE = ["oben links", "oben rechts", "unten rechts", "unten links"]


@dataclass
class MarkCandidate:
    x: float
    y: float
    side: float  # edge length in pixels


def _binarise(gray: np.ndarray) -> np.ndarray:
    """Dark ink as 255, paper as 0. Otsu's threshold, clamped to sane values."""
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    otsu, _ = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    threshold = float(np.clip(otsu, 90, 170))
    binary = np.where(blur < threshold, 255, 0).astype(np.uint8)
    # Remove isolated noise specks and close tiny gaps in the marks.
    kernel = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    return binary


def mark_candidates(gray: np.ndarray, expected_side_px: float) -> list[MarkCandidate]:
    """All solid, roughly square blobs of about the size of a corner mark."""
    binary = _binarise(gray)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = gray.shape
    min_area = (0.6 * expected_side_px) ** 2
    max_area = (1.5 * expected_side_px) ** 2
    found: list[MarkCandidate] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if not min_area <= area <= max_area:
            continue
        bx, by, bw, bh = cv2.boundingRect(contour)
        if bx <= 1 or by <= 1 or bx + bw >= w - 1 or by + bh >= h - 1:
            continue  # touches the image border: scanner shadow, not a mark
        (_, _), (rw, rh), _ = cv2.minAreaRect(contour)
        if min(rw, rh) / max(rw, rh) < 0.75:
            continue  # not square
        if area / (rw * rh) < 0.8:
            continue  # not solid (e.g. a QR finder pattern or a cross)
        hull_area = cv2.contourArea(cv2.convexHull(contour))
        if hull_area <= 0 or area / hull_area < 0.9:
            continue
        m = cv2.moments(contour)
        found.append(MarkCandidate(m["m10"] / m["m00"], m["m01"] / m["m00"], float(np.sqrt(area))))
    return found


def _consistent(corners: np.ndarray, aspect: float) -> bool:
    """Do the four points form the expected rectangle (allowing for skew and scale)?"""
    tl, tr, br, bl = corners
    top, bottom = np.linalg.norm(tr - tl), np.linalg.norm(br - bl)
    left, right = np.linalg.norm(bl - tl), np.linalg.norm(br - tr)
    if min(top, bottom, left, right) <= 0:
        return False
    if abs(top / bottom - 1) > 0.04 or abs(left / right - 1) > 0.04:
        return False
    measured = (left + right) / (top + bottom)
    return abs(measured / aspect - 1) < 0.06


def find_corner_marks(
    gray: np.ndarray, pixels_per_mm: float, layout: Layout
) -> tuple[np.ndarray | None, list[Problem]]:
    """Locate the corner mark centres as a (4, 2) array: TL, TR, BR, BL in image order.

    For each image corner the candidate nearest to it is taken; marks are the
    outermost solid squares on the sheet, so a blackened tick box further
    inside never wins over a present mark. If exactly one mark is missing it
    is estimated from the other three and reported.
    """
    problems: list[Problem] = []
    h, w = gray.shape
    expected = layout.params.mark_size * pixels_per_mm
    candidates = mark_candidates(gray, expected)
    image_corners = np.array([(0, 0), (w, 0), (w, h), (0, h)], dtype=float)

    chosen: list[np.ndarray | None] = []
    for cx, cy in image_corners:
        best, best_dist = None, None
        for c in candidates:
            if abs(c.x - cx) > 0.3 * w or abs(c.y - cy) > 0.3 * h:
                continue
            dist = np.hypot(c.x - cx, c.y - cy)
            if best_dist is None or dist < best_dist:
                best, best_dist = np.array([c.x, c.y]), dist
        chosen.append(best)

    missing = [i for i, c in enumerate(chosen) if c is None]
    if len(missing) > 1:
        names = ", ".join(CORNER_NAMES_DE[i] for i in missing)
        problems.append(Problem("no_corner_marks", f"Eckmarken nicht gefunden ({names})."))
        return None, problems
    if missing:
        i = missing[0]
        # Parallelogram completion: the missing corner is opposite + neighbours.
        chosen[i] = chosen[(i + 1) % 4] + chosen[(i + 3) % 4] - chosen[(i + 2) % 4]
        problems.append(
            Problem(
                "corner_mark_estimated",
                f"Eckmarke {CORNER_NAMES_DE[i]} fehlt; ihre Lage wurde aus den anderen drei geschätzt.",
            )
        )

    corners = np.array(chosen, dtype=float)
    aspect = layout.height / layout.width
    if w > h:  # landscape scan: the reader turns it before calling us, but be safe
        aspect = 1 / aspect
    if not _consistent(corners, aspect):
        problems.append(
            Problem(
                "no_corner_marks",
                "Die gefundenen Eckmarken bilden kein passendes Rechteck; die Seite wurde nicht gelesen.",
            )
        )
        return None, problems
    return corners, problems
