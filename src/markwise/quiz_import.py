"""Import a quiz of the Hands-on Computer Science platform (one Markdown file per language) into a pool.

A quiz folder holds `de.md` and `en.md`. After the front matter each question is a level-two heading, optionally
ending in `{#id}`, then perhaps a paragraph and a fenced code block, then the options as a task list, each option
with its feedback as an indented quote, and at the end a takeaway as a quote of its own:

    ## What do you see on the lamp when this program runs? {#aa-003}

    ```python static
    lamp.set_color(255, 0, 0)
    ```

    - [x] One second of red, then blue.
      > Correct: line by line.
    - [ ] Red and blue at once, so violet.
      > A program runs one line after the other.

    > The computer carries out the lines in the order in which they stand.

The languages are joined by identifier, or by position where a quiz has none. A question without an identifier
gets a new one from the pool; one whose text in the first language is already in the concept is not imported
twice. Every imported question is a draft for practice (`public: true`): releasing is the examiners' step.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import LiteralScalarString

from . import yamlio
from .pool import Pool
from .question import ordered, today

HEADING = re.compile(r"^## (.+?)\s*$")
ID_MARK = re.compile(r"\s*\{#([A-Za-z0-9-]+)\}\s*$")
OPTION = re.compile(r"^- \[([ xX])\] ?(.*)$")
FENCE = re.compile(r"^```(.*)$")
# "(Several answers may be correct.)", "(several are right)", "(Mehrere richtige Antworten möglich.)": the type
# says that, and the exam and the quiz print their own hint.
SEVERAL_HINT = re.compile(r"\s*\([^()]*\b(several|mehrere)\b[^()]*\)\s*$", re.IGNORECASE)
LEVELS = {"erinnern": "remember", "verstehen": "understand", "anwenden": "apply"}


@dataclass
class QuizQuestion:
    id: str | None
    stem: str
    several: bool  # the heading said several answers may be right
    code: str = ""
    code_language: str = ""
    options: list[dict] = field(default_factory=list)  # {correct, text, feedback}
    takeaway: str = ""


@dataclass
class QuizImportReport:
    concept: str = ""
    quiz_status: str = ""
    created: list[str] = field(default_factory=list)
    existing: list[str] = field(default_factory=list)  # already in the pool, left as they are
    problems: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def _join(lines: list[str]) -> str:
    """Markdown lines as text: soft line breaks become spaces, blank lines stay paragraph breaks."""
    paragraphs, current = [], []
    for line in lines:
        if line.strip():
            current.append(line.strip())
        elif current:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    return "\n\n".join(paragraphs)


def _quote(line: str, indent: str) -> str | None:
    """The text of a quote line with this indentation, or None when the line is not one."""
    if line.startswith(indent + ">"):
        return line[len(indent) + 1:].removeprefix(" ")
    return None


def front_matter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    _, head, body = text.split("---", 2)
    data = YAML(typ="safe").load(head) or {}
    return (data if isinstance(data, dict) else {}), body


def parse_quiz(path: Path) -> tuple[dict, list[QuizQuestion]]:
    """The front matter and the questions of one language file."""
    meta, body = front_matter(path.read_text(encoding="utf-8"))
    questions: list[QuizQuestion] = []
    blocks = re.split(r"^(?=## )", body, flags=re.M)
    for block in blocks:
        lines = block.rstrip().split("\n")
        heading = HEADING.match(lines[0])
        if not heading:
            continue
        title = heading.group(1)
        qid = None
        if m := ID_MARK.search(title):
            qid, title = m.group(1), title[:m.start()]
        several = bool(SEVERAL_HINT.search(title))
        title = SEVERAL_HINT.sub("", title).strip()
        q = QuizQuestion(qid, title, several)

        before, i = [], 1
        while i < len(lines) and not OPTION.match(lines[i]):
            fence = FENCE.match(lines[i])
            if fence:
                info = fence.group(1).split()
                q.code_language = info[0] if info else ""
                i += 1
                code = []
                while i < len(lines) and not lines[i].startswith("```"):
                    code.append(lines[i])
                    i += 1
                q.code = "\n".join(code)
            else:
                before.append(lines[i])
            i += 1
        extra = _join(before)
        if extra:
            q.stem = f"{q.stem}\n\n{extra}"

        takeaway: list[str] = []
        option = None
        feedback: list[str] = []
        for line in lines[i:]:
            if m := OPTION.match(line):
                if option is not None:
                    option["feedback"] = _join(feedback)
                option = {"correct": m.group(1) != " ", "text": [m.group(2)], "feedback": ""}
                feedback = []
                q.options.append(option)
            elif (quoted := _quote(line, "  ")) is not None and option is not None:
                feedback.append(quoted)
            elif (quoted := _quote(line, "")) is not None:
                takeaway.append(quoted)
            elif line.startswith("  ") and option is not None and not feedback:
                option["text"].append(line)  # an option text wrapped onto the next line
            elif not line.strip() and option is not None:
                option["feedback"] = _join(feedback) if feedback else option["feedback"]
                feedback = []
        if option is not None and feedback:
            option["feedback"] = _join(feedback)
        for o in q.options:
            o["text"] = _join(o["text"]) if isinstance(o["text"], list) else o["text"]
        q.takeaway = _join(takeaway)
        questions.append(q)
    return meta, questions


def _fingerprint(stem, code, options: list) -> str:
    """What makes a question the same question in the first language: its text, its code and its options."""
    return "|".join([str(stem or "").strip(), str(code or "").strip(), *(str(o or "").strip() for o in options)])


def _block(text: str):
    return LiteralScalarString(text + "\n") if "\n" in text else text


def _texts(values: dict[str, str]) -> CommentedMap:
    texts = CommentedMap((lang, _block(text)) for lang, text in values.items())
    if all("\n" not in v for v in values.values()):
        texts.fa.set_flow_style()
    return texts


def legacy_levels(folder: Path | str) -> dict[str, str]:
    """The level of each question in a folder of the earlier YAML format (`niveau`), by identifier."""
    levels = {}
    for path in sorted(Path(folder).glob("*/*.yaml")):
        data = yamlio.load(path)
        if data.get("niveau") in LEVELS:
            levels[str(data.get("id") or path.stem)] = LEVELS[data["niveau"]]
    return levels


def default_level(q: QuizQuestion) -> str:
    """Reading code is applying; without a level from elsewhere every other question counts as understanding."""
    return "apply" if q.code else "understand"


def default_seconds(qtype: str, has_code: bool) -> int:
    """A minute for one answer, half a minute more for judging several statements and for reading code."""
    return 60 + (30 if qtype == "multiple" else 0) + (30 if has_code else 0)


def import_quiz(pool: Pool, folder: Path | str, concept: str | None = None, name: str | None = None,
                levels: dict[str, str] | None = None, author: str = "") -> QuizImportReport:
    folder = Path(folder)
    concept = concept or folder.name.removesuffix("-quiz")
    report = QuizImportReport(concept=concept)
    languages = pool.settings.languages
    parsed = {}
    for lang in languages:
        path = folder / f"{lang}.md"
        if not path.exists():
            report.problems.append(f"{path} is missing")
            return report
        parsed[lang] = parse_quiz(path)
    metas = [parsed[lang][0] for lang in languages]
    report.quiz_status = next((str(m["status"]) for m in metas if m.get("status")), "")
    first = parsed[languages[0]][1]
    for lang in languages[1:]:
        if len(parsed[lang][1]) != len(first):
            report.problems.append(f"{lang}.md has {len(parsed[lang][1])} questions, {languages[0]}.md {len(first)}")
            return report

    if concept not in pool.concepts():
        settings = pool.settings
        titles = [str(m.get("title") or "") for m in metas]
        title = name or next((t for t in reversed(titles) if t), concept)
        settings.concepts = dict(settings.concepts or {})
        settings.concepts[concept] = {"name": re.sub(r"^(Quiz|Test):\s*", "", title), "description": ""}
        pool.write_settings()

    first_lang = languages[0]
    pick = lambda value: value.get(first_lang) if isinstance(value, dict) else value  # noqa: E731
    known = set()
    for path in sorted((pool.questions_dir / concept).glob("*.yaml")):
        data = yamlio.load(path)
        known.add(_fingerprint(pick(data.get("stem")), pick(data.get("code")),
                               [pick(o.get("text")) for o in data.get("options") or [] if isinstance(o, dict)]))

    levels = levels or {}
    for index, q in enumerate(first):
        versions = {lang: parsed[lang][1][index] for lang in languages}
        if q.id:
            versions = {lang: next((x for x in parsed[lang][1] if x.id == q.id), None) for lang in languages}
            if any(v is None for v in versions.values()):
                report.problems.append(f"{q.id}: not in every language")
                continue
        label = q.id or f"question {index + 1}"
        shapes = {lang: [o["correct"] for o in v.options] for lang, v in versions.items()}
        if len({tuple(s) for s in shapes.values()}) != 1:
            report.problems.append(f"{label}: options or correct answers differ between the languages")
            continue
        if q.id and q.id in pool.all_ids():
            report.existing.append(q.id)
            continue
        fingerprint = _fingerprint(q.stem, q.code, [o["text"] for o in q.options])
        if not q.id and fingerprint in known:
            report.existing.append(label)
            continue

        qid = q.id or pool.next_id(pool.id_prefix())
        n_correct = sum(1 for o in q.options if o["correct"])
        qtype = "multiple" if q.several or n_correct != 1 else "single"
        codes = {lang: v.code for lang, v in versions.items()}
        fields: dict = {
            "id": qid, "concept": concept, "type": qtype, "level": levels.get(qid) or default_level(q),
            "time_seconds": default_seconds(qtype, bool(q.code)), "status": "draft", "public": True,
            "stem": _texts({lang: v.stem for lang, v in versions.items()}),
        }
        if author:
            fields.update(created_by=author, created_at=today())
        if q.code:
            same = len(set(codes.values())) == 1
            fields["code"] = LiteralScalarString(q.code + "\n") if same else CommentedMap(
                (lang, LiteralScalarString(code + "\n")) for lang, code in codes.items())
            if q.code_language:
                fields["code_language"] = q.code_language
        options = []
        for k, option in enumerate(q.options):
            entry = CommentedMap(id=chr(ord("a") + k), correct=option["correct"],
                                 text=_texts({lang: v.options[k]["text"] for lang, v in versions.items()}))
            feedback = {lang: v.options[k]["feedback"] for lang, v in versions.items()}
            if any(feedback.values()):
                entry["feedback"] = _texts(feedback)
            options.append(entry)
        fields["options"] = options
        takeaway = {lang: v.takeaway for lang, v in versions.items()}
        if any(takeaway.values()):
            fields["takeaway"] = _texts(takeaway)
        path = pool.path_for(concept, qid)
        path.parent.mkdir(parents=True, exist_ok=True)
        yamlio.dump(ordered(fields), path)
        known.add(fingerprint)
        report.created.append(qid)
    return report
