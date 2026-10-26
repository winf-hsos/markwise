"""Typeset an exam with Typst: the question booklet, the answer sheet or the booklet with the boxes right below each
question, and the answer key.

Pages that are scanned carry the four corner marks and the QR code of the answer sheet (see `markwise.sheet`); the
first page of each booklet also carries the tick grid for the student number. Every tick box holds an invisible
marker. After typesetting, Typst reports where each marker landed, so the positions the scan reader looks at come
from the typeset booklet itself, whatever the length of the questions. They are written to `layout.json` next to
the PDFs.
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

import typst

from .exam import Exam
from .module import Module
from .pool import Pool
from .sheet.layout import BoxSpec, Layout, Rect, SheetParams
from .sheet.qr import encode_payload, qr_svg
from .text import unwrap

PARAMS = SheetParams()
BOX = PARAMS.box_size
FONTS = '("Arial", "Liberation Sans", "DejaVu Sans")'
LAYOUT_FILE = "layout.json"

# Where the content of a scanned page may go: clear of the marks, the QR code and the region opposite the QR code,
# which the reader keeps blank to tell an upside-down page.
SCAN_MARGINS = "(top: 44mm, bottom: 42mm, left: 22mm, right: 22mm)"
PLAIN_MARGINS = "(top: 22mm, bottom: 22mm, left: 22mm, right: 22mm)"

FILES = {
    "de": {"folder": "Druck", "booklet": "Klausurheft.pdf", "sheet": "Antwortbogen.pdf",
           "inline": "Klausurheft mit Antworten.pdf", "key": "Lösungsschlüssel.pdf"},
    "en": {"folder": "Print", "booklet": "Exam booklet.pdf", "sheet": "Answer sheet.pdf",
           "inline": "Exam booklet with answers.pdf", "key": "Answer key.pdf"},
}

WORDS = {
    "de": {
        "question": "Aufgabe", "points": "Punkte", "point": "Punkt", "date": "Datum", "time": "Bearbeitungszeit",
        "minutes": "Minuten", "total": "Gesamtpunktzahl", "name": "Name", "student": "Matrikelnummer",
        "booklet": "Heft", "page": "Seite", "examiners": "Prüfende",
        "how": "So beantworten Sie die Fragen",
        "tick": "Eine Antwort wählen Sie, indem Sie ihr Kästchen ankreuzen; Sie nehmen sie zurück, indem Sie das "
                "Kästchen vollständig ausmalen. Arbeiten Sie bitte mit einem dunklen Kugelschreiber oder Filzstift.",
        "single": "Genau eine Antwort ist richtig.", "multiple": "Eine oder mehrere Antworten sind richtig.",
        "sheet_note": "Kreuzen Sie Ihre Antworten auf dem Antwortbogen an. Nur der Antwortbogen wird bewertet.",
        "inline_note": "Kreuzen Sie Ihre Antworten direkt unter den Fragen an. Bitte trennen Sie keine Seiten heraus.",
        "student_note": "Tragen Sie Ihre Matrikelnummer oben in die Felder ein und kreuzen Sie darunter in jeder "
                        "Spalte die passende Ziffer an.",
        "answers": "Antworten", "free_text_here": "Antwort zu Aufgabe {n} im Antwortbogen.",
        "examiners_only": "Nur für Prüfende", "key": "Lösungsschlüssel", "correct": "richtig",
        "expected": "Erwartete Antwort", "marking": "Hinweise zur Bewertung", "not_scanned": "wird nicht gescannt",
        "fold": "bitte nicht knicken",
    },
    "en": {
        "question": "Question", "points": "points", "point": "point", "date": "Date", "time": "Time",
        "minutes": "minutes", "total": "Total points", "name": "Name", "student": "Student number",
        "booklet": "Booklet", "page": "Page", "examiners": "Examiners",
        "how": "How to answer",
        "tick": "Choose an answer by ticking its box; take it back by filling the box completely. Please use a dark "
                "ballpoint or felt-tip pen.",
        "single": "Exactly one answer is correct.", "multiple": "One or more answers are correct.",
        "sheet_note": "Tick your answers on the answer sheet. Only the answer sheet is marked.",
        "inline_note": "Tick your answers right below the questions. Please do not tear out any pages.",
        "student_note": "Write your student number into the fields at the top and tick the matching digit in each "
                        "column below.",
        "answers": "Answers", "free_text_here": "Answer question {n} on the answer sheet.",
        "examiners_only": "Examiners only", "key": "Answer key", "correct": "correct",
        "expected": "Expected answer", "marking": "Marking notes", "not_scanned": "not scanned",
        "fold": "please do not fold",
    },
}


class BookletError(Exception):
    """Something keeps the exam from being typeset; `code` names it for the interface."""

    def __init__(self, code: str, message: str, **params):
        super().__init__(message)
        self.code = code
        self.params = {k: str(v) for k, v in params.items()}


# --- the questions as the booklet shows them ---------------------------------------------


@dataclass
class Item:
    number: int
    id: str
    points: float
    type: str
    stem: str
    code: str = ""
    code_language: str = ""
    figures: list[Path] = field(default_factory=list)
    image_columns: int = 1
    options: list[dict] = field(default_factory=list)  # {id, text, correct, feedback}
    lines: int = 8
    half_points: bool = False
    expected: str = ""
    marking_notes: str = ""


def _pick(value, lang: str) -> str:
    return str(value.get(lang) or "") if isinstance(value, dict) else str(value or "")


def items_of(exam: Exam, module: Module) -> list[Item]:
    """The exam's questions in its language, in order; refuses an exam whose check finds errors."""
    errors = [f for f in exam.check(module) if f.severity == "error"]
    if errors:
        raise BookletError("booklet_errors", "the exam has errors: " + "; ".join(f.message for f in errors),
                           count=len(errors))
    if not exam.questions:
        raise BookletError("booklet_empty", "the exam has no questions")
    return [item_of(Pool.open(module.pool_root(entry.pool)), entry.id, exam.language, number, entry.points)
            for number, entry in enumerate(exam.questions, 1)]


def item_of(pool: Pool, qid: str, lang: str, number: int = 0, points: float = 0) -> Item:
    """One question as the booklet shows it, in one language."""
    q = pool.find(qid)
    figures = [path for name in q.images if (path := pool.image_file(name)) is not None]
    options = [{"id": str(o.get("id")), "text": _pick(o.get("text"), lang), "correct": o.get("correct") is True,
                "feedback": _pick(o.get("feedback"), lang)} for o in q.options if isinstance(o, dict)]
    return Item(
        number=number, id=q.id, points=points, type=q.type, stem=_pick(q.get("stem"), lang),
        code=str(q.get("code") or ""), code_language=str(q.get("code_language") or ""), figures=figures,
        image_columns=q.image_columns, options=options, lines=int(q.get("lines") or 8),
        half_points=q.get("half_points") is True, expected=_pick(q.get("expected"), lang),
        marking_notes=_pick(q.get("marking_notes"), lang),
    )


# --- Markdown to Typst ---------------------------------------------------------------------


def _s(text: str) -> str:
    """A Typst string literal."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


INLINE = re.compile(r"(`[^`\n]+`|\*\*[^*\n]+\*\*|\*[^*\n]+\*)")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")


def _inline(text: str) -> str:
    """One line of question text as Typst markup: **bold**, *italic* and `code`; everything else stays literal."""
    out = []
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith("`"):
            out.append(f"#raw({_s(part[1:-1])})")
        elif part.startswith("**"):
            out.append(f"#strong({_s(part[2:-2])})")
        elif part.startswith("*") and len(part) > 2:
            out.append(f"#emph({_s(part[1:-1])})")
        else:
            out.append(f"#{_s(part)}")
    return "".join(out)


def markdown(text: str) -> str:
    """Question text (Markdown as Markwise reads it) as Typst markup: paragraphs, lists, inline formatting."""
    blocks = []
    for block in re.split(r"\n\s*\n", unwrap(text or "")):
        lines = [line for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        if all(LIST_ITEM.match(line) for line in lines):
            items = ", ".join(f"[{_inline(LIST_ITEM.sub('', line))}]" for line in lines)
            blocks.append(f"#list({items})")
        else:
            blocks.append("#linebreak()".join(_inline(line.strip()) for line in lines))
    return "\n\n".join(blocks)


# --- pieces of the booklet -----------------------------------------------------------------


def _preamble(lang: str) -> str:
    return (
        f'#set text(font: {FONTS}, size: 10.5pt, lang: "{lang}")\n'
        "#set par(leading: 0.62em, spacing: 1.1em)\n"
        "#show raw: set text(font: (\"Cascadia Code\", \"Consolas\", \"DejaVu Sans Mono\"), size: 9pt)\n"
        # A tick box with its marker; the marker sits at the box's top-left corner.
        f"#let mwbox(id, kind: \"answer\", q: none, opt: none, pos: none, digit: none) = box(width: {BOX}mm, "
        f"height: {BOX}mm, stroke: {PARAMS.box_stroke_pt}pt + luma({PARAMS.box_stroke_grey}%), "
        "[#metadata((id: id, kind: kind, q: q, opt: opt, pos: pos, digit: digit))<mwbox>])\n"
    )


def _figures(item: Item, names: dict[Path, str]) -> str:
    if not item.figures:
        return ""
    columns = max(1, min(item.image_columns, len(item.figures)))
    cells = ", ".join(f'image("{names[path]}", width: 100%)' for path in item.figures)
    width = "100%" if columns > 1 else "70%"
    return f"#block(width: {width}, grid(columns: {columns}, gutter: 5mm, {cells}))\n"


def _code(item: Item) -> str:
    if not item.code.strip():
        return ""
    lang = f", lang: {_s(item.code_language)}" if item.code_language else ""
    return (f"#block(width: 100%, inset: 3mm, radius: 1.5mm, fill: luma(96%), "
            f"raw(block: true{lang}, {_s(item.code.rstrip())}))\n")


def _heading(item: Item, words: dict) -> str:
    unit = words["point"] if item.points == 1 else words["points"]
    hint = words["single"] if item.type == "single" else words["multiple"] if item.type == "multiple" else ""
    return (f"#block(below: 2mm, grid(columns: (1fr, auto), "
            f"text(weight: \"bold\", {_s(f'{words['question']} {item.number}')}), "
            f"text(size: 9pt, fill: luma(35%), {_s(f'{item.points:g} {unit}')})))\n"
            + (f"#text(size: 8.5pt, fill: luma(40%), {_s(hint)})\n\n" if hint else ""))


def _point_strip(item: Item, words: dict) -> str:
    """The grey boxes in which the examiner ticks the points of a free-text answer."""
    top = int(item.points)
    cells = []
    for value in range(top + 1):
        cells.append(f"stack(spacing: 1mm, align(center, text(size: 7pt, \"{value}\")), "
                     f"mwbox(\"p{item.number}-{value}\", kind: \"points\", q: {item.number}, opt: \"{value}\"))")
    if item.half_points:
        cells.append(f"stack(spacing: 1mm, align(center, text(size: 7pt, \"½\")), "
                     f"mwbox(\"p{item.number}-h\", kind: \"points\", q: {item.number}, opt: \"h\"))")
    return (f"#block(breakable: false, inset: 2.5mm, radius: 1mm, fill: luma(93%), grid(columns: 2, gutter: 4mm, "
            f"align(horizon, text(size: 8pt, fill: luma(30%), {_s(words['examiners_only'])})), "
            f"grid(columns: {len(cells)}, column-gutter: 2.2mm, {', '.join(cells)})))\n")


def _lines(count: int) -> str:
    return (f"#block(width: 100%, breakable: false, stack(spacing: 0mm, "
            + ", ".join(["block(width: 100%, height: 8mm, stroke: (bottom: 0.4pt + luma(70%)))"] * max(count, 1))
            + "))\n")


def _question(item: Item, words: dict, names: dict[Path, str], boxes: bool, free_text_answers: bool) -> str:
    """One question; with `boxes` the tick boxes stand left of the options and free text gets its answer area."""
    out = [_heading(item, words), markdown(item.stem), "\n\n", _figures(item, names), _code(item)]
    if item.type in ("single", "multiple"):
        rows = []
        for option in item.options:
            mark = (f"mwbox(\"q{item.number}{option['id']}\", q: {item.number}, opt: \"{option['id']}\")"
                    if boxes else "[]")
            rows.append(f"{mark}, text(weight: \"bold\", \"{option['id']}\"), [{markdown(option['text'])}]")
        out.append(f"#block(inset: (left: 2mm), grid(columns: ({BOX + 1.5}mm, 5mm, 1fr), row-gutter: 3.2mm, "
                   f"column-gutter: 1.5mm, {', '.join(rows)}))\n")
    elif free_text_answers:
        out.append(_lines(item.lines))
        out.append(_point_strip(item, words))
    else:
        out.append(f"#text(size: 9pt, style: \"italic\", {_s(words['free_text_here'].format(n=item.number))})\n")
    # A choice question stays on one page with its options; a free-text question may run on with its lines.
    breakable = "true" if item.type == "free_text" else "false"
    return f"#block(breakable: {breakable}, below: 9mm, [{''.join(out)}])\n"


def _cover_text(exam: Exam, items: list[Item], words: dict, module: Module, note: str) -> str:
    total = sum(i.points for i in items)
    facts = [(words["date"], exam.date), (words["total"], f"{total:g}")]
    if exam.examiners:
        facts.append((words["examiners"], ", ".join(exam.examiners)))
    rows = ", ".join(f"text(fill: luma(35%), {_s(k)}), {_s(v)}" for k, v in facts)
    return (
        f"#text(size: 9pt, fill: luma(35%), {_s(module.name)})\n\n"
        f"#text(size: 18pt, weight: \"bold\", {_s(exam.title)})\n\n"
        f"#grid(columns: 2, column-gutter: 6mm, row-gutter: 2.5mm, {rows})\n\n"
        f"#v(4mm)#grid(columns: (auto, 1fr), column-gutter: 3mm, align(bottom, {_s(words['name'] + ':')}), "
        "block(width: 100%, height: 7mm, stroke: (bottom: 0.5pt)))\n\n"
        f"#v(4mm)#block(width: 100%, inset: 4mm, radius: 1.5mm, stroke: 0.5pt + luma(75%), [#text(weight: \"bold\", "
        f"{_s(words['how'])})#parbreak()#text(size: 9.5pt, {_s(words['tick'])})#parbreak()"
        f"#text(size: 9.5pt, {_s(note)})])\n"
    )


def _scanned_page_setup(exam_code: str, words: dict, title: str) -> str:
    """Page set-up for scanned pages: corner marks, QR code per page, student number grid on each booklet's first
    page. `pages_per_booklet` and `qrs` are set by the caller; without QR codes yet, a placeholder of the same size."""
    p = PARAMS
    marks = ", ".join(f"({cx}mm, {cy}mm)" for cx, cy in p.mark_centres_page)
    student = []
    for pos in range(p.student_digits):
        x = p.student_left + pos * p.student_col_pitch
        student.append(f"place(top + left, dx: {x - 0.5}mm, dy: 30mm, rect(width: {p.box_size + 1}mm, height: 7mm, "
                       "stroke: 0.4pt + luma(65%)))")
        for digit in range(10):
            y = p.student_top + digit * p.student_row_pitch
            student.append(f"place(top + left, dx: {x}mm, dy: {y}mm, mwbox(\"s{pos + 1}-{digit}\", kind: \"student\", "
                           f"pos: {pos}, digit: {digit}))")
    for digit in range(10):
        y = p.student_top + digit * p.student_row_pitch
        student.append(f"place(top + left, dx: {p.student_left - 5.5}mm, dy: {y}mm, box(width: 4mm, height: {p.box_size}mm, "
                       f"align(right + horizon, text(size: 8pt, \"{digit}\"))))")
    student.append(f"place(top + left, dx: {p.student_left - 6}mm, dy: 24.5mm, text(size: 9pt, weight: \"bold\", "
                   f"{_s(words['student'])}))")
    student.append(f"place(top + left, dx: 84mm, dy: 42mm, block(width: 74mm, text(size: 8.5pt, {_s(words['student_note'])})))")
    return (
        f"#let marks = ({marks},)\n"
        "#let page-in-booklet(abs) = calc.rem(abs - 1, pages-per-booklet) + 1\n"
        "#let booklet-of(abs) = calc.quo(abs - 1, pages-per-booklet) + 1\n"
        f"#set page(width: {p.page_width}mm, height: {p.page_height}mm, margin: {SCAN_MARGINS}, background: context {{\n"
        f"  for (cx, cy) in marks {{ place(top + left, dx: cx - {p.mark_size / 2}mm, dy: cy - {p.mark_size / 2}mm, "
        f"rect(width: {p.mark_size}mm, height: {p.mark_size}mm, fill: black)) }}\n"
        "  let abs = here().page()\n"
        "  let pb = page-in-booklet(abs)\n"
        "  let bk = booklet-of(abs)\n"
        "  let key = str(bk) + \"-\" + str(pb)\n"
        f"  place(top + left, dx: {p.qr_left}mm, dy: {p.qr_top}mm, if key in qrs {{ image(bytes(qrs.at(key)), "
        f"format: \"svg\", width: {p.qr_size}mm) }} else {{ rect(width: {p.qr_size}mm, height: {p.qr_size}mm, "
        "stroke: 0.5pt + luma(85%)) })\n"
        f"  place(top + left, dx: 22mm, dy: 11.5mm, text(size: 11pt, weight: \"bold\", {_s(title)}))\n"
        f"  place(top + left, dx: 22mm, dy: 17.5mm, text(size: 8.5pt, fill: luma(30%), "
        f"{_s(exam_code + ' · ' + words['booklet'] + ' ')} + str(bk) + {_s(' · ' + words['page'] + ' ')} + str(pb)))\n"
        f"  place(top + left, dx: 40mm, dy: {p.page_height - 10.5}mm, box(width: {p.page_width - 80}mm, "
        f"align(center, text(size: 7pt, fill: luma(40%), {_s('Markwise · ' + exam_code + ' · ' + words['fold'])}))))\n"
        f"  if pb == 1 {{ {'; '.join(student)} }}\n"
        "})\n"
    )


def _positions_query() -> str:
    return ("#context [#metadata(query(<mwbox>).map(m => (v: m.value, page: m.location().page(), "
            "x: m.location().position().x / 1mm, y: m.location().position().y / 1mm)))<mwpos>]\n")


# --- compiling ----------------------------------------------------------------------------------


@dataclass
class Typeset:
    pdf: bytes
    boxes: list[dict]
    pages: int


def _compile(body: str, build: Path, query: bool) -> Typeset:
    source = build / "main.typ"
    source.write_text(body + (_positions_query() if query else ""), encoding="utf-8")
    pdf = typst.compile(str(source), root=str(build))
    boxes = []
    if query:
        boxes = json.loads(typst.query(str(source), "<mwpos>", field="value", one=True, root=str(build)))
    import pymupdf
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        pages = doc.page_count
    return Typeset(pdf, boxes, pages)


def _qr_dict(code: str, booklets: int, pages: int) -> str:
    entries = []
    for bk in range(1, booklets + 1):
        for pg in range(1, pages + 1):
            svg = qr_svg(encode_payload(code, 0, pg, f"{bk:03d}"))
            entries.append(f"\"{bk}-{pg}\": {_s(svg)}")
    return "#let qrs = (" + ", ".join(entries) + (",)" if len(entries) == 1 else ")") + "\n"


def _scanned(content: str, setup: str, code: str, booklets: int, build: Path) -> tuple[bytes, list[dict], int]:
    """Typeset scanned booklets in two passes: first one booklet, to learn its length and where its boxes are;
    then all booklets with their QR codes. Each booklet ends on an even page, so that double-sided copies of
    several booklets never share a sheet."""
    head = "#let pages-per-booklet = 1000\n#let qrs = (:)\n"
    first = _compile(head + setup + content, build, query=True)
    per_booklet = first.pages + first.pages % 2
    one = content + ("\n#pagebreak()#hide[.]\n" if first.pages % 2 else "")  # an empty back page
    copies = "\n#pagebreak()\n".join([one] * booklets)
    full = (f"#let pages-per-booklet = {per_booklet}\n" + _qr_dict(code, booklets, per_booklet) + setup + copies)
    final = _compile(full, build, query=False)
    expected = per_booklet * booklets
    if final.pages != expected:
        raise BookletError("booklet_pages", f"the booklets came out with {final.pages} pages, expected {expected}")
    return final.pdf, first.boxes, per_booklet


# --- the layout for the reader ----------------------------------------------------------------


def _layout_boxes(found: list[dict]) -> list[dict]:
    """Marker positions (top-left of each box, page coordinates) as box centres in the mark system."""
    origin = PARAMS.mark_centres_page[0]
    out = []
    for entry in found:
        v = entry["v"]
        out.append({
            "page": entry["page"], "id": v["id"], "kind": v["kind"],
            "x": round(entry["x"] + BOX / 2 - origin[0], 3), "y": round(entry["y"] + BOX / 2 - origin[1], 3),
            "size": BOX, "question": v.get("q"), "option": v.get("opt"),
            "digit_position": v.get("pos"), "digit": v.get("digit"),
        })
    return out


def page_layout(layout_file: Path | str, page: int) -> Layout:
    """The reader's layout for one page of a booklet, from `layout.json`."""
    data = json.loads(Path(layout_file).read_text(encoding="utf-8"))
    p = PARAMS
    tl, tr, br, _ = p.mark_centres_page
    qr = Rect(p.qr_left - tl[0], p.qr_top - tl[1], p.qr_size, p.qr_size)
    boxes = [BoxSpec(**{k: v for k, v in b.items() if k != "page"}) for b in data["boxes"] if b["page"] == page]
    return Layout(params=p, width=tr[0] - tl[0], height=br[1] - tl[1], origin=tl, qr=qr, boxes=boxes)


# --- the documents --------------------------------------------------------------------------


def exam_code(exam: Exam) -> str:
    """A short identifier for the QR codes: the date and the initials of the title."""
    initials = "".join(word[0] for word in re.findall(r"[A-Za-zÄÖÜäöü0-9]+", exam.title))[:5].upper()
    return f"{exam.date.replace('-', '')}-{initials or 'EX'}"


@dataclass
class Printed:
    folder: Path
    files: list[Path]
    pages_per_booklet: int
    booklets: int


def print_exam(exam: Exam, module: Module | None = None, booklets: int = 1) -> Printed:
    """Typeset the exam into its print folder: question booklet and answer sheet, or the booklet with the boxes
    below the questions; the answer key; and `layout.json` for reading the scans."""
    module = module or Module.around(exam.root)
    items = items_of(exam, module)
    lang = exam.language if exam.language in WORDS else "de"
    words, files = WORDS[lang], FILES[lang]
    folder = exam.root / files["folder"]
    code = exam_code(exam)
    output: dict[str, bytes] = {}  # goes to the folder once everything is typeset
    booklets = max(1, int(booklets))

    with tempfile.TemporaryDirectory() as tmp:
        build = Path(tmp)
        names: dict[Path, str] = {}
        for item in items:
            for path in item.figures:
                if path not in names:
                    names[path] = f"fig{len(names)}{path.suffix.lower()}"
                    shutil.copy2(path, build / names[path])

        setup = _preamble(lang) + _scanned_page_setup(code, words, exam.title)
        cover_space = "#v(64mm)\n"  # the student number grid sits above, in the page background

        if exam.answers == "inline":
            content = (cover_space + _cover_text(exam, items, words, module, words["inline_note"])
                       + "#pagebreak()\n" + "".join(_question(i, words, names, True, True) for i in items))
            pdf, found, per = _scanned(content, setup, code, booklets, build)
            output[files["inline"]] = pdf
        else:
            plain = (f"#set page(width: 210mm, height: 297mm, margin: {PLAIN_MARGINS}, footer: context align(center, "
                     f"text(size: 8pt, fill: luma(40%), {_s(exam.title + ' · ' + words['page'] + ' ')} + "
                     "counter(page).display())))\n")
            booklet = (plain + _preamble(lang) + _cover_text(exam, items, words, module, words["sheet_note"])
                       + "#pagebreak()\n" + "".join(_question(i, words, names, False, False) for i in items))
            output[files["booklet"]] = _compile(booklet, build, query=False).pdf

            choice = [i for i in items if i.type in ("single", "multiple")]
            free = [i for i in items if i.type == "free_text"]
            rows = []
            for i in choice:
                cells = [f"text(weight: \"bold\", \"{i.number}\")"]
                cells += [f"stack(spacing: 1mm, align(center, text(size: 7.5pt, \"{o['id']}\")), "
                          f"mwbox(\"q{i.number}{o['id']}\", q: {i.number}, opt: \"{o['id']}\"))" for o in i.options]
                rows.append(f"grid(columns: {len(cells)}, column-gutter: 3mm, align: horizon, {', '.join(cells)})")
            grid = (f"#text(weight: \"bold\", {_s(words['answers'])})\n\n#columns(2, gutter: 10mm)["
                    + "".join(f"#block(below: 4.5mm, {row})" for row in rows) + "]\n") if rows else ""
            answers = "".join(
                f"#block(breakable: true, below: 9mm, [#text(weight: \"bold\", {_s(words['question'] + ' ' + str(i.number))})"
                f"#parbreak(){_lines(i.lines)}{_point_strip(i, words)}])\n" for i in free)
            content = cover_space + grid + ("#pagebreak()\n" + answers if answers else "")
            pdf, found, per = _scanned(content, setup, code, booklets, build)
            output[files["sheet"]] = pdf

        layout = {"version": 1, "exam": code, "answers": exam.answers, "language": lang,
                  "pages_per_booklet": per, "booklets": booklets, "boxes": _layout_boxes(found)}
        output[LAYOUT_FILE] = (json.dumps(layout, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
        output[files["key"]] = _compile(_answer_key(exam, items, words, module, lang), build, query=False).pdf

    folder.mkdir(exist_ok=True)
    try:
        # A print in the other answer form would not match the new layout, so the last print goes as a whole.
        for name in [files[k] for k in ("booklet", "sheet", "inline", "key")] + [LAYOUT_FILE]:
            (folder / name).unlink(missing_ok=True)
        for name, data in output.items():
            (folder / name).write_bytes(data)
    except PermissionError as exc:
        name = Path(exc.filename).name if exc.filename else files["folder"]
        raise BookletError("booklet_file_open", f"{name} is open in another program", file=name) from None
    return Printed(folder, [folder / name for name in output], per, booklets)


def printed_files(exam: Exam) -> list[dict]:
    """What lies in the exam's print folder from the last printing, in the order it was written."""
    files = FILES[exam.language if exam.language in FILES else "de"]
    folder = exam.root / files["folder"]
    order = [files[k] for k in ("booklet", "sheet", "inline", "key")] + [LAYOUT_FILE]
    return [{"name": name, "path": str(folder / name), "modified": (folder / name).stat().st_mtime}
            for name in order if (folder / name).exists()]


def _answer_key(exam: Exam, items: list[Item], words: dict, module: Module, lang: str) -> str:
    parts = [f"#set page(width: 210mm, height: 297mm, margin: {PLAIN_MARGINS})\n", _preamble(lang),
             f"#text(size: 9pt, fill: luma(35%), {_s(module.name + ' · ' + exam.date)})\n\n",
             f"#text(size: 16pt, weight: \"bold\", {_s(words['key'] + ': ' + exam.title)})\n\n"]
    for item in items:
        unit = words["point"] if item.points == 1 else words["points"]
        body = [f"#text(weight: \"bold\", {_s(f'{words['question']} {item.number}')}) "
                f"#text(size: 9pt, fill: luma(40%), {_s(f'({item.id}, {item.points:g} {unit})')})\n\n",
                markdown(item.stem), "\n\n"]
        if item.options:
            rows = []
            for o in item.options:
                tick = f"text(fill: rgb(\"#1f8452\"), weight: \"bold\", {_s('✓ ' + words['correct'])})" if o["correct"] else "[]"
                rows.append(f"text(weight: \"bold\", \"{o['id']}\"), [{markdown(o['text'])}], {tick}")
            body.append(f"#grid(columns: (5mm, 1fr, auto), row-gutter: 2.5mm, column-gutter: 2mm, {', '.join(rows)})\n")
        if item.type == "free_text":
            body.append(f"#text(weight: \"bold\", size: 9.5pt, {_s(words['expected'])})\n\n{markdown(item.expected)}\n\n")
            if item.marking_notes.strip():
                body.append(f"#text(weight: \"bold\", size: 9.5pt, {_s(words['marking'])})\n\n{markdown(item.marking_notes)}\n\n")
        parts.append(f"#block(breakable: true, below: 7mm, [{''.join(body)}])\n")
    return "".join(parts)
