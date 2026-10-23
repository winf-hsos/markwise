"""A question: a thin view over its YAML mapping, so that saving keeps everything Markwise does not edit."""

from __future__ import annotations

import datetime
import os
from pathlib import Path
from typing import Any

from ruamel.yaml.comments import CommentedMap

from . import yamlio

TYPES = ("single", "multiple", "free_text")
LEVELS = ("remember", "understand", "apply")
STATUSES = ("draft", "reviewed", "piloted", "retired")

# How long answering a question takes, in seconds, when nobody chose otherwise.
DEFAULT_SECONDS = {"single": 60, "multiple": 60, "free_text": 300}

# Settings a variant takes from the question it varies, unless it sets them itself. Its texts are its own.
INHERITED = ("type", "level", "time_seconds", "coverage", "misconception")

# Order of the known top-level fields when Markwise writes a new file.
FIELD_ORDER = (
    "id", "concept", "type", "level", "time_seconds", "status", "public", "exam", "variant_of", "reviewed_by",
    "created_by", "created_at", "changed_by", "changed_at",
    "coverage", "misconception", "session",
    "stem", "image", "images", "image_columns", "code", "code_language",
    "options",
    "half_points", "lines", "expected", "marking_notes",
)


class ConflictError(Exception):
    """The file changed on disk since it was loaded, for example by a colleague in a shared folder."""


class Question:
    def __init__(self, data: CommentedMap, path: Path | None = None):
        self.data = data
        self.path = path
        self.parent: Question | None = None  # for a variant: the question it varies, once the pool has linked it
        self._mtime_ns = path.stat().st_mtime_ns if path and path.exists() else None

    @classmethod
    def load(cls, path: Path) -> "Question":
        return cls(yamlio.load(path), path)

    # --- fields ---------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """A field of the file; for a variant, an inherited setting it does not set itself comes from the parent."""
        if key not in self.data and key in INHERITED and self.variant_of and self.parent is not None:
            return self.parent.data.get(key, default)
        return self.data.get(key, default)

    def inherited(self) -> dict:
        """The settings this variant takes from its parent at the moment, by field."""
        if not self.variant_of or self.parent is None:
            return {}
        return {key: self.parent.data[key] for key in INHERITED if key not in self.data and key in self.parent.data}

    @property
    def id(self) -> str:
        return str(self.data.get("id", ""))

    @property
    def concept(self) -> str:
        return str(self.data.get("concept", ""))

    @property
    def type(self) -> str:
        return str(self.get("type", ""))

    @property
    def level(self) -> str:
        return str(self.get("level", ""))

    @property
    def status(self) -> str:
        return str(self.data.get("status", ""))

    @property
    def public(self) -> bool:
        """Shown to students for practice."""
        return self.data.get("public") is True

    @property
    def exam(self) -> bool:
        """May be drawn for an exam. Without the field: exactly the questions that are not public."""
        value = self.data.get("exam")
        return value if isinstance(value, bool) else not self.public

    @property
    def variant_of(self) -> str | None:
        value = self.data.get("variant_of")
        return str(value) if value else None

    @property
    def options(self) -> list:
        value = self.data.get("options")
        return value if isinstance(value, list) else []

    @property
    def images(self) -> list[str]:
        """The figures below the question text: one in `image`, several in `images`."""
        many = self.data.get("images")
        if isinstance(many, list):
            return [str(name) for name in many if name]
        one = self.data.get("image")
        return [str(one)] if one else []

    @property
    def image_columns(self) -> int:
        """How several figures are laid out: 1 one below the other, n in n columns."""
        value = self.data.get("image_columns")
        return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 1

    @property
    def correct_ids(self) -> list[str]:
        return [str(o.get("id")) for o in self.options if isinstance(o, dict) and o.get("correct") is True]

    def text(self, lang: str) -> str:
        stem = self.data.get("stem")
        return str(stem.get(lang, "")) if isinstance(stem, dict) else ""

    def summary(self) -> dict:
        """The fields lists and the command line show."""
        return {
            "id": self.id,
            "concept": self.concept,
            "type": self.type,
            "level": self.level,
            "status": self.status,
            "public": self.public,
            "exam": self.exam,
            "variant_of": self.variant_of,
            "path": str(self.path) if self.path else None,
        }

    # --- saving ---------------------------------------------------------------------

    def changed_on_disk(self) -> bool:
        if self.path is None or self._mtime_ns is None:
            return False
        return not self.path.exists() or self.path.stat().st_mtime_ns != self._mtime_ns

    def save(self, path: Path | None = None, force: bool = False) -> None:
        target = path or self.path
        if target is None:
            raise ValueError("no file to save the question to")
        if not force and target == self.path and self.changed_on_disk():
            raise ConflictError(f"{target} changed on disk since it was loaded")
        yamlio.dump(self.data, target)
        self.path = target
        self._mtime_ns = target.stat().st_mtime_ns


def today() -> datetime.date:
    """As a date, so that YAML writes it without quotes."""
    return datetime.date.today()


def default_author() -> str:
    """Who is working: the name given in the settings, else the Windows user name."""
    from . import settings
    return settings.load().examiner.strip() or os.environ.get("USERNAME") or os.environ.get("USER") or ""


def ordered(fields: dict) -> CommentedMap:
    """A new mapping with the known fields in their usual order and any other fields after the metadata."""
    result = CommentedMap()
    known = [k for k in FIELD_ORDER if k in fields]
    others = [k for k in fields if k not in FIELD_ORDER]
    split = FIELD_ORDER.index("stem")
    for key in [k for k in known if FIELD_ORDER.index(k) < split] + others + [k for k in known if FIELD_ORDER.index(k) >= split]:
        result[key] = fields[key]
    return result


def insert_field(data: CommentedMap, key: str, value) -> None:
    """Put a new field where it belongs in the usual order."""
    rank = FIELD_ORDER.index(key)
    position = len(data)
    for i, existing in enumerate(data):
        if existing in FIELD_ORDER and FIELD_ORDER.index(existing) > rank:
            position = i
            break
    data.insert(position, key, value)


def template(qid: str, concept: str, qtype: str, languages: list[str], n_options: int = 4,
             author: str = "") -> CommentedMap:
    """An empty question of the given type, ready to be filled in."""
    if qtype not in TYPES:
        raise ValueError(f"unknown type {qtype!r}")
    texts = lambda: CommentedMap((lang, "") for lang in languages)  # noqa: E731
    fields: dict = {
        "id": qid, "concept": concept, "type": qtype, "level": "understand",
        "time_seconds": DEFAULT_SECONDS[qtype], "status": "draft", "public": True, "stem": texts(),
    }
    if author:
        fields.update(created_by=author, created_at=today())
    if qtype == "free_text":
        fields.update(half_points=False, lines=8, expected=texts(), marking_notes=texts())
    else:
        options = []
        for i in range(n_options):
            option = CommentedMap(id=chr(ord("a") + i), correct=(i == 0), text=texts(), feedback=texts())
            option["text"].fa.set_flow_style()
            option["feedback"].fa.set_flow_style()
            options.append(option)
        fields["options"] = options
    return ordered(fields)
