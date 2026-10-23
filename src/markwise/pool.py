"""A question pool: a folder with pool.toml and one YAML file per question, free of personal data."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import tomli_w

from .question import Question, template

POOL_FILE = "pool.toml"
MIN_OPTIONS_ALLOWED = 4  # § 5 (3) a of the general examination regulations


@dataclass
class PoolSettings:
    name: str
    languages: list[str] = field(default_factory=lambda: ["de", "en"])
    min_options: int = 4
    max_options: int = 5
    concepts: list[str] | None = None  # None: the folder names under questions/ are the concepts

    def to_toml(self) -> dict:
        data = {
            "name": self.name,
            "languages": self.languages,
            "min_options": self.min_options,
            "max_options": self.max_options,
        }
        if self.concepts is not None:
            data["concepts"] = self.concepts
        return data


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
            concepts=list(raw["concepts"]) if "concepts" in raw else None,
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
