"""Geometry of the answer sheet.

All layout parameters live in :class:`SheetParams`. :func:`build_layout` turns
them into a :class:`Layout` that lists every printed element the scanner cares
about (corner marks, QR code, tick boxes). The same layout drives the Typst
renderer and the scan reader, so positions are never duplicated.

Coordinates in a :class:`Layout` are millimetres in the *mark system*: the
origin is the centre of the top-left corner mark, x grows to the right and y
grows downwards. The centres of the four corner marks are therefore
``(0, 0)``, ``(width, 0)``, ``(width, height)`` and ``(0, height)``. Page
coordinates (origin at the top-left page corner) are only needed for printing
and are obtained with :meth:`Layout.to_page`.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

LAYOUT_VERSION = 1


@dataclass(frozen=True)
class SheetParams:
    """Every tunable number of the answer sheet, in millimetres unless noted."""

    page_width: float = 210.0
    page_height: float = 297.0

    # Corner marks: solid squares; the inset is measured from the page edge
    # to the outer edge of the mark.
    mark_size: float = 5.0
    mark_inset: float = 10.0

    # Tick boxes.
    box_size: float = 4.5
    box_stroke_pt: float = 0.6  # outline width in typographic points
    box_stroke_grey: int = 25  # outline colour, percent luma (0 = black)

    # Multiple-choice answers.
    questions: int = 40
    options: str = "abcde"
    questions_per_column: int = 20
    answer_top: float = 108.0  # top edge of the first box row, page coordinates
    label_width: float = 8.0  # space for the question number left of the boxes
    option_pitch: float = 7.5  # horizontal distance between box origins
    row_pitch: float = 7.0  # vertical distance between box origins
    group_size: int = 5  # an extra gap after every n questions helps the eye
    group_gap: float = 2.0
    column_gap: float = 25.0  # from the last box of a column to the next label

    # Student number tick grid: one column per digit, rows 0 to 9.
    student_digits: int = 7
    student_left: float = 28.0  # left edge of the first box, page coordinates
    student_top: float = 40.0  # top edge of the row for digit 0
    student_col_pitch: float = 6.5
    student_row_pitch: float = 6.0

    # QR code (top right). The opposite corner region, rotated by 180 degrees,
    # must stay blank: the reader uses the contrast between both to tell an
    # upside-down page from an upright one.
    qr_size: float = 22.0
    qr_left: float = 168.0
    qr_top: float = 17.0

    @property
    def mark_centres_page(self) -> list[tuple[float, float]]:
        """Centres of the corner marks in page coordinates: TL, TR, BR, BL."""
        c = self.mark_inset + self.mark_size / 2
        r = self.page_width - c
        b = self.page_height - c
        return [(c, c), (r, c), (r, b), (c, b)]


@dataclass(frozen=True)
class BoxSpec:
    """One tick box. ``x`` and ``y`` are the box centre in the mark system."""

    id: str
    kind: str  # "answer" or "student"
    x: float
    y: float
    size: float
    question: int | None = None
    option: str | None = None
    digit_position: int | None = None  # 0-based position within the number
    digit: int | None = None


@dataclass(frozen=True)
class Rect:
    """An axis-aligned rectangle in the mark system (top-left corner and size)."""

    x: float
    y: float
    width: float
    height: float

    def rotated_180(self, frame_width: float, frame_height: float) -> "Rect":
        """The same rectangle after turning the page by 180 degrees."""
        return Rect(
            frame_width - self.x - self.width,
            frame_height - self.y - self.height,
            self.width,
            self.height,
        )


@dataclass(frozen=True)
class Layout:
    """Everything the reader needs to know about a sheet, in the mark system."""

    params: SheetParams
    width: float  # distance between left and right mark centres
    height: float  # distance between top and bottom mark centres
    origin: tuple[float, float]  # top-left mark centre in page coordinates
    qr: Rect
    boxes: list[BoxSpec] = field(default_factory=list)
    version: int = LAYOUT_VERSION

    # -- coordinate helpers -------------------------------------------------

    def to_page(self, x: float, y: float) -> tuple[float, float]:
        """Convert a point from the mark system to page coordinates."""
        return x + self.origin[0], y + self.origin[1]

    def from_page(self, x: float, y: float) -> tuple[float, float]:
        """Convert a point from page coordinates to the mark system."""
        return x - self.origin[0], y - self.origin[1]

    @property
    def mark_centres(self) -> list[tuple[float, float]]:
        """Corner mark centres in the mark system: TL, TR, BR, BL."""
        return [(0.0, 0.0), (self.width, 0.0), (self.width, self.height), (0.0, self.height)]

    def answer_boxes(self) -> list[BoxSpec]:
        return [b for b in self.boxes if b.kind == "answer"]

    def student_boxes(self) -> list[BoxSpec]:
        return [b for b in self.boxes if b.kind == "student"]

    # -- serialisation ------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "units": "mm",
            "coordinates": (
                "origin at the centre of the top-left corner mark, x to the right, "
                "y downwards; box x/y are box centres"
            ),
            "width": self.width,
            "height": self.height,
            "origin_on_page": list(self.origin),
            "mark_size": self.params.mark_size,
            "box_size": self.params.box_size,
            "qr": asdict(self.qr),
            "params": asdict(self.params),
            "boxes": [asdict(b) for b in self.boxes],
        }

    def to_json(self, path: str | Path | None = None) -> str:
        text = json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
        if path is not None:
            Path(path).write_text(text + "\n", encoding="utf-8")
        return text

    @classmethod
    def from_dict(cls, data: dict) -> "Layout":
        if data.get("version") != LAYOUT_VERSION:
            raise ValueError(f"unsupported layout version: {data.get('version')!r}")
        return cls(
            params=SheetParams(**data["params"]),
            width=float(data["width"]),
            height=float(data["height"]),
            origin=tuple(data["origin_on_page"]),
            qr=Rect(**data["qr"]),
            boxes=[BoxSpec(**b) for b in data["boxes"]],
        )

    @classmethod
    def from_json(cls, path: str | Path) -> "Layout":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def answer_column_lefts(p: SheetParams) -> list[float]:
    """Left edge (page coordinates) of each answer column's number label.

    The columns are centred horizontally on the page.
    """
    columns = -(-p.questions // p.questions_per_column)
    column_width = p.label_width + (len(p.options) - 1) * p.option_pitch + p.box_size
    total = columns * column_width + (columns - 1) * p.column_gap
    left = (p.page_width - total) / 2
    return [left + i * (column_width + p.column_gap) for i in range(columns)]


def answer_row_top(p: SheetParams, row: int) -> float:
    """Top edge (page coordinates) of the box row with the given 0-based index."""
    return p.answer_top + row * p.row_pitch + (row // p.group_size) * p.group_gap


def build_layout(params: SheetParams | None = None) -> Layout:
    """Compute the positions of all scanned elements from the parameters."""
    p = params or SheetParams()
    tl, tr, br, _bl = p.mark_centres_page
    origin = tl
    width = tr[0] - tl[0]
    height = br[1] - tl[1]
    half = p.box_size / 2

    def mark_xy(page_x: float, page_y: float) -> tuple[float, float]:
        return round(page_x - origin[0], 4), round(page_y - origin[1], 4)

    boxes: list[BoxSpec] = []

    # Student number: column = digit position, row = digit value.
    for pos in range(p.student_digits):
        for digit in range(10):
            left = p.student_left + pos * p.student_col_pitch
            top = p.student_top + digit * p.student_row_pitch
            x, y = mark_xy(left + half, top + half)
            boxes.append(
                BoxSpec(
                    id=f"s{pos + 1}-{digit}",
                    kind="student",
                    x=x,
                    y=y,
                    size=p.box_size,
                    digit_position=pos,
                    digit=digit,
                )
            )

    # Answers: questions run down the first column, then the next one.
    lefts = answer_column_lefts(p)
    for q in range(1, p.questions + 1):
        col, row = divmod(q - 1, p.questions_per_column)
        top = answer_row_top(p, row)
        for k, option in enumerate(p.options):
            left = lefts[col] + p.label_width + k * p.option_pitch
            x, y = mark_xy(left + half, top + half)
            boxes.append(
                BoxSpec(
                    id=f"q{q}{option}",
                    kind="answer",
                    x=x,
                    y=y,
                    size=p.box_size,
                    question=q,
                    option=option,
                )
            )

    qx, qy = mark_xy(p.qr_left, p.qr_top)
    qr = Rect(qx, qy, p.qr_size, p.qr_size)
    return Layout(params=p, width=width, height=height, origin=origin, qr=qr, boxes=boxes)
