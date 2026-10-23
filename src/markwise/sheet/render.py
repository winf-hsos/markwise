"""Typeset answer sheets with Typst.

Every element is placed absolutely from the :class:`~markwise.sheet.layout.Layout`,
so the printed sheet and the reader's expectations come from the same numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import typst

from .layout import Layout, SheetParams, answer_column_lefts, answer_row_top, build_layout
from .qr import encode_payload, qr_svg

FONTS = '("Arial", "Liberation Sans", "DejaVu Sans")'


@dataclass(frozen=True)
class SheetPage:
    """What distinguishes one printed answer sheet page from another."""

    exam: str = "TEST"
    variant: int = 0
    page: int = 1
    booklet: str = "001"
    title: str = "Markwise · Antwortbogen"

    @property
    def payload(self) -> str:
        return encode_payload(self.exam, self.variant, self.page, self.booklet)


def _mm(value: float) -> str:
    return f"{value:.3f}mm"


def _string(text: str) -> str:
    """A Typst string literal."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def _place(x: float, y: float, body: str) -> str:
    return f"#place(top + left, dx: {_mm(x)}, dy: {_mm(y)}, {body})\n"


def _label(x: float, y: float, w: float, h: float, text: str, align: str, size: float = 8) -> str:
    """A text label in a fixed box, aligned inside it (page coordinates)."""
    body = (
        f"box(width: {_mm(w)}, height: {_mm(h)}, "
        f"align({align}, text(size: {size}pt, {_string(text)})))"
    )
    return _place(x, y, body)


def _page_source(layout: Layout, page: SheetPage) -> str:
    p: SheetParams = layout.params
    out: list[str] = []
    stroke = f"{p.box_stroke_pt}pt + luma({p.box_stroke_grey}%)"

    # Corner marks.
    for cx, cy in p.mark_centres_page:
        s = p.mark_size
        out.append(_place(cx - s / 2, cy - s / 2, f"rect(width: {_mm(s)}, height: {_mm(s)}, fill: black)"))

    # Header.
    out.append(_place(22, 11.5, f"text(size: 13pt, weight: \"bold\", {_string(page.title)})"))
    info = f"Prüfung {page.exam} · Variante {page.variant} · Bogen {page.booklet} · Seite {page.page}"
    out.append(_place(22, 18.5, f"text(size: 9pt, {_string(info)})"))

    # QR code.
    qx, qy = layout.to_page(layout.qr.x, layout.qr.y)
    svg = qr_svg(page.payload)
    out.append(_place(qx, qy, f'image(bytes({_string(svg)}), format: "svg", width: {_mm(layout.qr.width)})'))

    # Student number: handwriting boxes (not scanned), digit labels, tick grid.
    out.append(_label(p.student_left - 6, 25.5, 60, 4, "Matrikelnummer", "left + horizon", 9))
    for pos in range(p.student_digits):
        x = p.student_left + pos * p.student_col_pitch - 0.5
        out.append(_place(x, 30.0, f"rect(width: {_mm(p.box_size + 1)}, height: 7mm, stroke: 0.4pt + luma(65%))"))
    for digit in range(10):
        y = p.student_top + digit * p.student_row_pitch
        out.append(_label(p.student_left - 5.5, y, 4, p.box_size, str(digit), "right + horizon", 8))

    # Instructions next to the student number.
    sample = f"box(width: 3.2mm, height: 3.2mm, stroke: {stroke}, baseline: 0.5mm"
    cross = (
        f"#{sample}, place(line(start: (0%, 0%), end: (100%, 100%), stroke: 0.9pt))"
        f" + place(line(start: (100%, 0%), end: (0%, 100%), stroke: 0.9pt)))"
    )
    filled = f"#{sample}, fill: black)"
    instructions = (
        "block(width: 70mm)[#set par(leading: 0.55em, spacing: 0.9em)\n"
        "#text(size: 9pt, weight: \"bold\")[So füllen Sie den Bogen aus]\n\n"
        "#text(size: 8.5pt)[Arbeiten Sie bitte mit einem dunklen Kugelschreiber oder Filzstift. "
        f"Eine Antwort wählen Sie, indem Sie ihr Kästchen ankreuzen {cross}, und Sie nehmen sie zurück, "
        f"indem Sie das Kästchen vollständig ausmalen {filled}.]\n\n"
        "#text(size: 8.5pt)[Tragen Sie Ihre Matrikelnummer oben in die Felder ein und kreuzen Sie "
        "darunter in jeder Spalte die passende Ziffer an.]]"
    )
    out.append(_place(84, 30, instructions))

    # Answer grid: option letters above each column, question numbers left.
    lefts = answer_column_lefts(p)
    for left in lefts:
        for k, option in enumerate(p.options):
            x = left + p.label_width + k * p.option_pitch
            out.append(_label(x, p.answer_top - 5, p.box_size, 4, option, "center + bottom", 8))
    for box in layout.boxes:
        bx, by = layout.to_page(box.x - box.size / 2, box.y - box.size / 2)
        out.append(_place(bx, by, f"rect(width: {_mm(box.size)}, height: {_mm(box.size)}, stroke: {stroke})"))
    for q in range(1, p.questions + 1):
        col, row = divmod(q - 1, p.questions_per_column)
        y = answer_row_top(p, row)
        out.append(_label(lefts[col], y, p.label_width - 2, p.box_size, str(q), "right + horizon", 9))

    # Footer between the bottom marks.
    footer = f"Markwise · {page.exam} · Bogen {page.booklet} · Seite {page.page} · bitte nicht knicken"
    out.append(_label(40, p.page_height - 10.5, p.page_width - 80, 4, footer, "center + horizon", 7))
    return "".join(out)


def sheet_typst_source(pages: list[SheetPage], layout: Layout | None = None) -> str:
    """Typst source for a document with one answer sheet per entry of ``pages``."""
    layout = layout or build_layout()
    p = layout.params
    head = (
        f"#set page(width: {_mm(p.page_width)}, height: {_mm(p.page_height)}, margin: 0mm)\n"
        f'#set text(font: {FONTS}, lang: "de")\n'
    )
    body = "#pagebreak()\n".join(_page_source(layout, page) for page in pages)
    return head + body


def render_sheet_pdf(
    pages: list[SheetPage], out_path: str | Path | None = None, layout: Layout | None = None
) -> bytes:
    """Compile the answer sheets to PDF; optionally write them to ``out_path``."""
    source = sheet_typst_source(pages, layout)
    pdf = typst.compile(source.encode("utf-8"))
    if out_path is not None:
        Path(out_path).write_bytes(pdf)
    return pdf
