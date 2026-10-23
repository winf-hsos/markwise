"""A question pool: a folder with pool.toml and one YAML file per question, free of personal data."""

from __future__ import annotations

import re
import shutil
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import tomli_w

from .question import Question, template

POOL_FILE = "pool.toml"
MIN_OPTIONS_ALLOWED = 4  # § 5 (3) a of the general examination regulations
IMAGE_TYPES = (".svg", ".png", ".jpg", ".jpeg")  # an image is named without its extension in a question
UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "ae", "Ö": "oe", "Ü": "ue"})


def slugify(name: str) -> str:
    """The identifier of a concept, made from its name: `Zahlensysteme und Codes` becomes `zahlensysteme-und-codes`."""
    text = name.translate(UMLAUTS).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "concept"


def name_from_id(concept_id: str) -> str:
    """A readable stand-in for a concept that has no name yet."""
    return concept_id.replace("-", " ").capitalize()


@dataclass
class PoolSettings:
    name: str
    languages: list[str] = field(default_factory=lambda: ["de", "en"])
    min_options: int = 4
    max_options: int = 5
    # id -> {"name": ..., "description": ...}; None: the folder names under questions/ are the concepts
    concepts: dict[str, dict] | None = None

    def to_toml(self) -> dict:
        data = {
            "name": self.name,
            "languages": self.languages,
            "min_options": self.min_options,
            "max_options": self.max_options,
        }
        if self.concepts is not None:
            data["concepts"] = {cid: {k: v for k, v in info.items() if v} for cid, info in self.concepts.items()}
        return data


def _read_concepts(raw) -> dict[str, dict]:
    """Concepts as a table of names and descriptions; the earlier plain list of identifiers is read as well."""
    if isinstance(raw, list):
        return {str(cid): {} for cid in raw}
    return {str(cid): {"name": str(info.get("name", "")), "description": str(info.get("description", ""))}
            for cid, info in raw.items()}


@dataclass
class LoadError:
    path: Path
    message: str


class Pool:
    def __init__(self, root: Path, settings: PoolSettings):
        self.root = root
        self.settings = settings

    @property
    def questions_dir(self) -> Path:
        return self.root / "questions"

    @property
    def images_dir(self) -> Path:
        return self.root / "images"

    @classmethod
    def open(cls, path: Path | str) -> "Pool":
        path = Path(path)
        root = path.parent if path.name == POOL_FILE else path
        settings_file = root / POOL_FILE
        if not settings_file.exists():
            raise FileNotFoundError(f"no {POOL_FILE} in {root}")
        with open(settings_file, "rb") as f:
            raw = tomllib.load(f)
        settings = PoolSettings(
            name=raw.get("name", root.name),
            languages=list(raw.get("languages", ["de", "en"])),
            min_options=int(raw.get("min_options", 4)),
            max_options=int(raw.get("max_options", 5)),
            concepts=_read_concepts(raw["concepts"]) if "concepts" in raw else None,
        )
        return cls(root, settings)

    @classmethod
    def create(cls, root: Path | str, settings: PoolSettings) -> "Pool":
        root = Path(root)
        if (root / POOL_FILE).exists():
            raise FileExistsError(f"{root / POOL_FILE} already exists")
        if settings.min_options < MIN_OPTIONS_ALLOWED:
            raise ValueError(f"at least {MIN_OPTIONS_ALLOWED} options are required")
        (root / "questions").mkdir(parents=True, exist_ok=True)
        (root / "images").mkdir(exist_ok=True)
        pool = cls(root, settings)
        pool.write_settings()
        return pool

    def write_settings(self) -> None:
        (self.root / POOL_FILE).write_text(tomli_w.dumps(self.settings.to_toml()), encoding="utf-8")

    # --- questions ------------------------------------------------------------------

    def question_files(self) -> list[Path]:
        if not self.questions_dir.exists():
            return []
        return sorted(self.questions_dir.glob("*/*.yaml"))

    def load(self) -> tuple[list[Question], list[LoadError]]:
        questions, errors = [], []
        for path in self.question_files():
            try:
                questions.append(Question.load(path))
            except Exception as exc:  # a broken file must not stop the rest of the pool
                errors.append(LoadError(path, f"cannot be read: {exc}"))
        return questions, errors

    def concepts(self) -> list[str]:
        if self.settings.concepts is not None:
            return list(self.settings.concepts)
        if not self.questions_dir.exists():
            return []
        return sorted(p.name for p in self.questions_dir.iterdir() if p.is_dir())

    def image_file(self, name: str) -> Path | None:
        """The file behind a question's image name: the SVG for the screen if there is one, else the first match."""
        for ext in ("",) + IMAGE_TYPES:
            candidate = self.images_dir / f"{name}{ext}"
            if candidate.is_file():
                return candidate
        return None

    def image_names(self) -> list[str]:
        if not self.images_dir.is_dir():
            return []
        return sorted({p.stem for p in self.images_dir.iterdir() if p.suffix.lower() in IMAGE_TYPES})

    def add_image(self, source: Path | str) -> str:
        """Copy an image into the pool's images folder; returns the name questions use for it."""
        source = Path(source)
        if source.suffix.lower() not in IMAGE_TYPES:
            raise ValueError(f"{source.name} is not an image Markwise can use ({', '.join(IMAGE_TYPES)})")
        self.images_dir.mkdir(parents=True, exist_ok=True)
        base = slugify(source.stem)
        name, n = base, 2
        while any((self.images_dir / f"{name}{ext}").exists() for ext in IMAGE_TYPES):
            existing = self.image_file(name)
            if existing is not None and existing.read_bytes() == source.read_bytes():
                return name  # the same picture is there already
            name, n = f"{base}-{n}", n + 1
        shutil.copy2(source, self.images_dir / f"{name}{source.suffix.lower()}")
        return name

    def concept_info(self) -> list[dict]:
        """Every concept with its name and short description, sorted by name."""
        defined = self.settings.concepts or {}
        result = []
        for cid in self.concepts():
            info = defined.get(cid, {})
            result.append({"id": cid, "name": info.get("name") or name_from_id(cid),
                           "description": info.get("description", ""), "named": bool(info.get("name"))})
        return sorted(result, key=lambda c: c["name"].lower())

    def add_concept(self, name: str, description: str = "") -> str:
        """Define a new concept by its name; returns the identifier made from the name."""
        name = name.strip()
        if not name:
            raise ValueError("a concept needs a name")
        if self.settings.concepts is None:  # from now on the pool keeps a list, starting with its folders
            self.settings.concepts = {cid: {} for cid in self.concepts()}  # unnamed until someone names them
        if any(info.get("name", "").lower() == name.lower() for info in self.settings.concepts.values()):
            raise ValueError(f"a concept named {name!r} exists already")
        base = slugify(name)
        cid, n = base, 2
        while cid in self.settings.concepts or (self.questions_dir / cid).exists():
            cid, n = f"{base}-{n}", n + 1
        self.settings.concepts[cid] = {"name": name, "description": description.strip()}
        (self.questions_dir / cid).mkdir(parents=True, exist_ok=True)
        self.write_settings()
        return cid

    def update_concept(self, cid: str, name: str | None = None, description: str | None = None) -> None:
        """Rename or describe a concept; its identifier and folder stay."""
        if cid not in self.concepts():
            raise KeyError(f"no concept {cid}")
        if self.settings.concepts is None:
            self.settings.concepts = {c: {} for c in self.concepts()}
        info = self.settings.concepts.setdefault(cid, {})
        if name is not None:
            if not name.strip():
                raise ValueError("a concept needs a name")
            info["name"] = name.strip()
        if description is not None:
            info["description"] = description.strip()
        self.write_settings()

    def path_for(self, concept: str, qid: str) -> Path:
        return self.questions_dir / concept / f"{qid}.yaml"

    def find(self, qid: str) -> Question:
        matches = list(self.questions_dir.glob(f"*/{qid}.yaml"))
        if not matches:
            raise KeyError(f"no question {qid} in {self.root}")
        return Question.load(matches[0])

    def all_ids(self) -> set[str]:
        return {p.stem for p in self.question_files()}

    def next_id(self, prefix: str) -> str:
        """The next free identifier with the prefix; retired numbers are never reused because their files stay."""
        pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
        numbers = [int(m.group(1)) for qid in self.all_ids() if (m := pattern.match(qid))]
        return f"{prefix}-{max(numbers, default=0) + 1:03d}"

    def prefix_for(self, concept: str) -> str:
        """The prefix used by existing questions of the concept, else the initials of the concept name."""
        folder = self.questions_dir / concept
        if folder.exists():
            for path in sorted(folder.glob("*.yaml")):
                if "-" in path.stem:
                    return path.stem.rsplit("-", 1)[0]
        return "".join(part[0] for part in concept.split("-") if part) or "q"

    def new_question(self, concept: str, qtype: str) -> Question:
        qid = self.next_id(self.prefix_for(concept))
        path = self.path_for(concept, qid)
        question = Question(template(qid, concept, qtype, self.settings.languages, self.settings.min_options))
        question.save(path)
        return question

    def delete(self, qid: str, used_in_exam: bool) -> str:
        """Remove a draft that never was in an exam; retire everything else. Returns what happened."""
        question = self.find(qid)
        if used_in_exam or question.status != "draft":
            question.data["status"] = "retired"
            question.save()
            return "retired"
        question.path.unlink()
        return "deleted"
