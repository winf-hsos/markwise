"""An exam: exam.toml in its own folder below the module, with the questions chosen by hand, in their order, and
their points, and optionally divided into sections ("Teil A", "Teil B" …). A section starts before a question and
runs until the next section; the questions are numbered straight through.

While an exam is being put together it refers to its questions in the module's pools. Freezing it, which comes
later, copies them into the exam folder so that the exam stays complete whatever happens to the pools.
"""

from __future__ import annotations

import datetime
import math
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import tomli_w

from .checks import ERROR, NOTE, WARNING, Finding, check_question
from .module import EXAM_FILE, Module
from .pool import Pool
from .question import default_author

ANSWER_MODES = ("sheet", "inline")  # a separate answer sheet, or the boxes right below each question
LANGUAGES = ("de", "en")
UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def suggest_points(seconds: int | None) -> float:
    """One point per minute of answering time, rounded to half points, at least one."""
    if not seconds:
        return 1.0
    return max(1.0, round(seconds / 60 * 2) / 2)


def semester_of(date: datetime.date) -> str:
    """The semester an exam date falls in: April to September is the summer semester, October to March the winter."""
    if 4 <= date.month <= 9:
        return f"{date.year} - SS"
    start = date.year if date.month >= 10 else date.year - 1
    return f"{start}-{str(start + 1)[2:]} - WS"


def folder_title(title: str) -> str:
    """A title as part of a folder name: without characters Windows does not allow."""
    return re.sub(r"\s+", " ", UNSAFE.sub("", title)).strip(" .") or "Klausur"


@dataclass
class ExamQuestion:
    pool: str  # the pool as the module refers to it
    id: str
    points: float


@dataclass
class ExamSection:
    id: str  # stable while the exam is put together, for the interface
    title: str
    note: str = ""  # a few words for the students below the title
    before: int = 0  # the section starts before this question (0-based); len(questions) for one at the end
    pool: str = ""  # optionally the concept the section draws from: its pool as the module refers to it …
    concept: str = ""  # … and the concept's identifier in that pool


@dataclass
class Exam:
    root: Path
    title: str
    date: str
    semester: str
    language: str = "de"
    answers: str = "sheet"
    examiners: list[str] = field(default_factory=list)
    questions: list[ExamQuestion] = field(default_factory=list)
    sections: list[ExamSection] = field(default_factory=list)
    created_by: str = ""
    created_at: str = ""

    @property
    def file(self) -> Path:
        return self.root / EXAM_FILE

    @classmethod
    def open(cls, path: Path | str) -> "Exam":
        path = Path(path)
        root = path.parent if path.name == EXAM_FILE else path
        with open(root / EXAM_FILE, "rb") as f:
            raw = tomllib.load(f)
        return cls(
            root=root,
            title=str(raw.get("title", root.name)),
            date=str(raw.get("date", "")),
            semester=str(raw.get("semester", "")),
            language=str(raw.get("language", "de")),
            answers=str(raw.get("answers", "sheet")),
            examiners=[str(e) for e in raw.get("examiners", [])],
            questions=[ExamQuestion(str(q["pool"]), str(q["id"]), float(q.get("points", 1)))
                       for q in raw.get("questions", [])],
            sections=[ExamSection(str(s.get("id") or f"s{i + 1}"), str(s.get("title", "")), str(s.get("note", "")),
                                  int(s.get("before", 0)), str(s.get("pool", "")), str(s.get("concept", "")))
                      for i, s in enumerate(raw.get("sections", []))],
            created_by=str(raw.get("created_by", "")),
            created_at=str(raw.get("created_at", "")),
        )

    @classmethod
    def create(cls, module: Module, title: str, date: str, language: str = "de", answers: str = "sheet",
               semester: str = "", author: str | None = None) -> "Exam":
        title = title.strip()
        if not title:
            raise ValueError("an exam needs a title")
        day = datetime.date.fromisoformat(date)
        if language not in LANGUAGES:
            raise ValueError(f"unknown language {language}")
        if answers not in ANSWER_MODES:
            raise ValueError(f"unknown answer mode {answers}")
        semester = semester.strip() or semester_of(day)
        root = module.new_exam_folder(semester, day.isoformat(), folder_title(title))
        if (root / EXAM_FILE).exists():
            raise FileExistsError(f"{root} already holds an exam")
        root.mkdir(parents=True, exist_ok=True)
        exam = cls(root, title, day.isoformat(), semester, language, answers,
                   created_by=default_author() if author is None else author, created_at=datetime.date.today().isoformat())
        exam.save()
        return exam

    def rename(self, module: Module, title: str, date: str) -> None:
        """Give the exam a new title or date; its folder follows, into another semester if the date says so.
        Printed booklets and everything else in the folder move with it."""
        title = title.strip()
        if not title:
            raise ValueError("an exam needs a title")
        day = datetime.date.fromisoformat(date)
        semester = semester_of(day)
        target = module.new_exam_folder(semester, day.isoformat(), folder_title(title))
        same = target.exists() and target.samefile(self.root)  # also a change of case only, on Windows
        if target.exists() and not same:
            raise FileExistsError(f"{target} exists already")
        if target != self.root:
            target.parent.mkdir(parents=True, exist_ok=True)
            self.root.rename(target)
            self.root = target
        self.title, self.date, self.semester = title, day.isoformat(), semester
        self.save()

    def save(self) -> None:
        data = {
            "title": self.title,
            "date": self.date,
            "semester": self.semester,
            "language": self.language,
            "answers": self.answers,
            "examiners": self.examiners,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "questions": [{"pool": q.pool, "id": q.id, "points": q.points} for q in self.questions],
            "sections": [{k: v for k, v in (("id", s.id), ("title", s.title), ("note", s.note), ("before", s.before),
                                            ("pool", s.pool if s.concept else ""), ("concept", s.concept)) if v != ""}
                         for s in self.sections],
        }
        self.file.write_text(tomli_w.dumps({k: v for k, v in data.items() if v not in ("", None, [])
                                            or k == "questions"}), encoding="utf-8")

    # --- sections ------------------------------------------------------------------------

    def flat(self) -> list[ExamQuestion | ExamSection]:
        """Questions and sections in one list, each section right before its first question."""
        out: list[ExamQuestion | ExamSection] = []
        starts = sorted(self.sections, key=lambda s: s.before)  # stable: sections at the same place keep their order
        k = 0
        for i, question in enumerate(self.questions):
            while k < len(starts) and starts[k].before <= i:
                out.append(starts[k])
                k += 1
            out.append(question)
        out.extend(starts[k:])
        return out

    def set_flat(self, items: list[ExamQuestion | ExamSection]) -> None:
        """Take questions and sections from one list, as `flat` gives it."""
        self.questions, self.sections = [], []
        for item in items:
            if isinstance(item, ExamSection):
                item.before = len(self.questions)
                self.sections.append(item)
            else:
                self.questions.append(item)

    def new_section_id(self) -> str:
        taken = {s.id for s in self.sections}
        return next(f"s{n}" for n in range(1, len(taken) + 2) if f"s{n}" not in taken)

    def section_of(self, index: int) -> ExamSection | None:
        """The section a question (by its place) belongs to, if any."""
        found = None
        for section in sorted(self.sections, key=lambda s: s.before):
            if section.before <= index:
                found = section
        return found

    # --- the questions ---------------------------------------------------------------------

    def pool_ref(self, module: Module, pool_path: Path | str) -> str:
        """How the module refers to a pool given by its folder."""
        target = Path(pool_path).resolve()
        for ref in module.pools:
            if module.pool_root(ref) == target:
                return ref
        raise KeyError(f"{pool_path} is not a pool of this module")

    def add(self, module: Module, pool_path: Path | str, qid: str, points: float | None = None) -> ExamQuestion:
        ref = self.pool_ref(module, pool_path)
        if any(q.pool == ref and q.id == qid for q in self.questions):
            raise ValueError(f"{qid} is in the exam already")
        question = Pool.open(module.pool_root(ref)).find(qid)
        entry = ExamQuestion(ref, qid, float(points) if points is not None else suggest_points(question.get("time_seconds")))
        self.questions.append(entry)
        return entry

    def total_points(self) -> float:
        return sum(q.points for q in self.questions)

    def section_points(self, section: ExamSection) -> float:
        return sum(q.points for i, q in enumerate(self.questions) if self.section_of(i) is section)

    # --- checking ------------------------------------------------------------------------

    def check(self, module: Module) -> list[Finding]:
        """What keeps the exam from being printed (errors) or deserves a look (warnings)."""
        out: list[Finding] = []

        def add(severity, qid, code, message, **params):
            out.append(Finding(severity, qid, message, None, code, {k: str(v) for k, v in params.items()}))

        if not self.questions:
            add(NOTE, None, "exam_empty", "the exam has no questions yet")
        if len(self.examiners) < 2:
            add(NOTE, None, "exam_examiners", "fewer than two examiners are entered", count=len(self.examiners))
        pools: dict[str, Pool | None] = {}
        parents: dict[str, list[str]] = {}
        seen = set()
        for index, entry in enumerate(self.questions):
            if entry.pool not in pools:
                root = module.pool_root(entry.pool)
                pools[entry.pool] = Pool.open(root) if (root / "pool.toml").exists() else None
            pool = pools[entry.pool]
            key = (entry.pool, entry.id)
            if key in seen:
                add(ERROR, entry.id, "exam_duplicate", f"{entry.id} is in the exam twice", id=entry.id)
            seen.add(key)
            if pool is None:
                add(ERROR, entry.id, "exam_pool_missing", f"the pool of {entry.id} is not found", id=entry.id)
                continue
            try:
                question = pool.find(entry.id)
            except KeyError:
                add(ERROR, entry.id, "exam_question_missing", f"{entry.id} is not in its pool any more", id=entry.id)
                continue
            if question.status == "retired":
                add(ERROR, entry.id, "exam_retired", f"{entry.id} is retired", id=entry.id)
            if not question.exam:
                add(WARNING, entry.id, "exam_practice_only", f"{entry.id} is meant for practice only", id=entry.id)
            if any(f.severity == ERROR for f in check_question(question, pool)):
                add(ERROR, entry.id, "exam_question_errors", f"{entry.id} has errors", id=entry.id)
            stem = question.get("stem")
            if not (isinstance(stem, dict) and str(stem.get(self.language) or "").strip()):
                add(ERROR, entry.id, "exam_language", f"{entry.id} has no text in {self.language}", id=entry.id, lang=self.language)
            if not entry.points > 0 or math.isnan(entry.points):
                add(ERROR, entry.id, "exam_points", f"{entry.id} needs more than 0 points", id=entry.id)
            section = self.section_of(index)
            if section and section.concept and (section.pool, section.concept) != (entry.pool, question.concept):
                add(WARNING, entry.id, "exam_section_concept", f"{entry.id} is not about the concept of {section.title}",
                    id=entry.id, title=section.title)
            family = question.variant_of or question.id
            parents.setdefault(f"{entry.pool}|{family}", []).append(entry.id)
        for section in self.sections:
            if not section.title.strip():
                add(WARNING, None, "exam_section_title", "a section has no title", section=section.id)
            if not any(self.section_of(i) is section for i in range(len(self.questions))):
                add(WARNING, None, "exam_section_empty", f"section {section.title} has no questions",
                    section=section.id, title=section.title)
        for ids in parents.values():
            if len(ids) > 1:
                add(WARNING, ids[0], "exam_same_family", f"{', '.join(ids)} are variants of the same question",
                    ids=", ".join(ids))
        return out


def exams_of(module: Module) -> list[Exam]:
    return [Exam.open(path) for path in module.exams()]
