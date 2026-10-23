"""Result types of the scan reader."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any

import numpy as np

# Box states.
EMPTY = "empty"
TICKED = "ticked"
DOUBTFUL = "doubtful"

# Reasons for a doubtful box.
REASON_FILLED = "filled"  # box blackened almost completely: possibly a correction
REASON_HEAVY = "heavy"  # more ink than a cross, less than a filled box
REASON_PARTIAL = "partial"  # a small dark stroke, e.g. half a tick
REASON_FAINT = "faint"  # only light marks, e.g. pencil or an erased tick


@dataclass
class Problem:
    """Something that went wrong on a page. ``code`` is stable, ``message`` is German."""

    code: str
    message: str


@dataclass
class BoxReading:
    """The reading of one tick box."""

    id: str
    kind: str  # "answer" or "student"
    state: str  # EMPTY, TICKED or DOUBTFUL
    fill_ratio: float  # share of the inner area covered by dark ink (0..1)
    faint_ratio: float  # share of the inner area with any visible mark (0..1)
    darkness: float  # mean darkness of the inner area (0 = paper, 1 = black ink)
    reason: str | None = None  # why the box is doubtful
    question: int | None = None
    option: str | None = None
    digit_position: int | None = None
    digit: int | None = None
    x: float = 0.0  # box centre where it was found, mark system (mm)
    y: float = 0.0
    shift: tuple[float, float] = (0.0, 0.0)  # found minus expected position (mm)


@dataclass
class PageResult:
    """Everything read from one scanned page."""

    page_index: int  # 0-based page number in the PDF
    problems: list[Problem] = field(default_factory=list)
    qr_text: str | None = None
    qr: dict[str, str] | None = None
    upside_down: bool = False
    corners_px: list[tuple[float, float]] | None = None  # TL, TR, BR, BL in the rendered page
    white_level: float | None = None
    black_level: float | None = None
    boxes: list[BoxReading] = field(default_factory=list)
    student_number: str | None = None  # digits, '?' where unclear; None if no grid
    # Straightened page (mark system canvas, greyscale) for crops and debug images.
    image: np.ndarray | None = field(default=None, repr=False)
    pixels_per_mm: float = 0.0
    margin_mm: float = 0.0

    @property
    def read(self) -> bool:
        """Whether the boxes could be read at all (corner marks found)."""
        return bool(self.boxes)

    def box(self, box_id: str) -> BoxReading:
        for b in self.boxes:
            if b.id == box_id:
                return b
        raise KeyError(box_id)

    def answers(self) -> dict[int, list[str]]:
        """Ticked options per question (doubtful boxes are not included)."""
        result: dict[int, list[str]] = {}
        for b in self.boxes:
            if b.kind == "answer":
                result.setdefault(b.question, [])
                if b.state == TICKED:
                    result[b.question].append(b.option)
        return result

    def doubtful(self) -> list[BoxReading]:
        return [b for b in self.boxes if b.state == DOUBTFUL]

    def to_dict(self) -> dict[str, Any]:
        # Built by hand so that the page image is neither copied nor exported.
        data = {f.name: getattr(self, f.name) for f in fields(self) if f.name != "image"}
        data["problems"] = [asdict(p) for p in self.problems]
        data["boxes"] = [asdict(b) for b in self.boxes]
        data["answers"] = {str(k): v for k, v in self.answers().items()}
        return data


@dataclass
class ScanResult:
    """All pages of one scanned PDF."""

    source: str
    pages: list[PageResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "pages": [p.to_dict() for p in self.pages]}
