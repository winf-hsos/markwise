"""QR payload of an answer sheet page and its SVG rendering.

The payload is a short ``key=value`` list separated by semicolons and starts
with a format tag, for example ``MW1;exam=TEST;var=0;page=1;bk=001``. Short
payloads keep the QR code at a low version with large modules, which reads
more reliably from a copier scan.
"""

from __future__ import annotations

import io

import segno

FORMAT_TAG = "MW1"


def encode_payload(exam: str, variant: int, page: int, booklet: str) -> str:
    """Build the QR text for one page of an answer booklet."""
    for name, value in (("exam", exam), ("booklet", booklet)):
        if any(c in str(value) for c in ";="):
            raise ValueError(f"{name} must not contain ';' or '=': {value!r}")
    return f"{FORMAT_TAG};exam={exam};var={variant};page={page};bk={booklet}"


def parse_payload(text: str) -> dict[str, str] | None:
    """Parse a QR text into a dict; returns ``None`` if it is not a Markwise code."""
    parts = text.strip().split(";")
    if not parts or parts[0] != FORMAT_TAG:
        return None
    data: dict[str, str] = {"format": FORMAT_TAG}
    for part in parts[1:]:
        key, sep, value = part.partition("=")
        if not sep:
            return None
        data[key] = value
    return data


def qr_svg(text: str) -> str:
    """Render the QR code as SVG without quiet zone (the sheet keeps it blank)."""
    code = segno.make_qr(text, error="m")
    buffer = io.BytesIO()
    code.save(buffer, kind="svg", border=0, xmldecl=False, svgns=True, nl=False, dark="#000")
    return buffer.getvalue().decode("utf-8")
