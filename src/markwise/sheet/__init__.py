"""Answer sheets: layout, QR payload and typesetting with Typst."""

from .layout import BoxSpec, Layout, Rect, SheetParams, build_layout
from .qr import encode_payload, parse_payload
from .render import SheetPage, render_sheet_pdf, sheet_typst_source

__all__ = [
    "BoxSpec",
    "Layout",
    "Rect",
    "SheetPage",
    "SheetParams",
    "build_layout",
    "encode_payload",
    "parse_payload",
    "render_sheet_pdf",
    "sheet_typst_source",
]
