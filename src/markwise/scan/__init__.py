"""Scan reading: corner marks, orientation, QR code and tick boxes."""

from .debug import crop_box, debug_image
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
from .reader import Thresholds, classify, looks_like_cross, pdf_page_images, read_page_image, read_pdf

__all__ = [
    "DOUBTFUL",
    "EMPTY",
    "REASON_FAINT",
    "REASON_FILLED",
    "REASON_HEAVY",
    "REASON_PARTIAL",
    "TICKED",
    "BoxReading",
    "PageResult",
    "Problem",
    "ScanResult",
    "Thresholds",
    "classify",
    "crop_box",
    "debug_image",
    "looks_like_cross",
    "pdf_page_images",
    "read_page_image",
    "read_pdf",
]
