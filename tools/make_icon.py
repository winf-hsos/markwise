"""Draw the Markwise logo, a white tick on a filled rounded square, as the favicon and as the Windows icon.

    python tools\\make_icon.py

writes frontend/public/favicon.svg (shown in the window and copied into the build) and
src/markwise/app/markwise.ico (window, taskbar and Start menu entry), the latter with one PNG per size.
"""

from __future__ import annotations

import struct
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
GREEN = "#1f8452"  # the accent colour of the interface
SIZES = (16, 24, 32, 48, 64, 128, 256)


def logo(stroke: float = 7) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">'
        f'<rect x="3" y="3" width="58" height="58" rx="14" fill="{GREEN}"/>'
        f'<path d="M18.5 33.5 27.5 42.5 45.5 22" fill="none" stroke="#fff" stroke-width="{stroke}" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>\n'
    )


def png(svg: str, size: int) -> bytes:
    page = pymupdf.open(stream=svg.encode(), filetype="svg")[0]
    zoom = size / page.rect.width
    return page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=True).tobytes("png")


def ico(images: list[tuple[int, bytes]]) -> bytes:
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries, data = b"", b""
    for size, image in images:
        side = 0 if size >= 256 else size  # 0 stands for 256 in an icon directory
        entries += struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32, len(image), offset + len(data))
        data += image
    return header + entries + data


def main() -> None:
    (ROOT / "frontend" / "public" / "favicon.svg").write_text(logo(), encoding="utf-8")
    # Small sizes get a bolder tick, so that it still reads at 16 pixels.
    images = [(size, png(logo(9 if size <= 24 else 7), size)) for size in SIZES]
    (ROOT / "src" / "markwise" / "app" / "markwise.ico").write_bytes(ico(images))
    print("favicon.svg and markwise.ico written")


if __name__ == "__main__":
    main()
