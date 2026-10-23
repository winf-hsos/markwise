"""Rules every question of a pool has to follow."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from .pool import Pool
from .question import LEVELS, STATUSES, TYPES, Question

ERROR, WARNING, NOTE = "error", "warning", "note"

# An option this many times longer than the average of the others may give the answer away.
LENGTH_FACTOR = 1.8
LENGTH_MIN_CHARS = 25


@dataclass
class Finding:
    severity: str
    question: str | None
    message: str
    path: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _texts(value, languages: list[str]) -> list[str]:
    """Languages missing or empty in a {lang: text} mapping."""
    if not isinstance(value, dict):
        return list(languages)
    return [lang for lang in languages if not str(value.get(lang) or "").strip()]


def check_question(q: Question, pool: Pool) -> list[Finding]:
    s = pool.settings
    out: list[Finding] = []

    def add(severity: str, message: str) -> None:
        out.append(Finding(severity, q.id or q.path.stem, message, str(q.path)))

    for key in ("id", "concept", "type", "level", "status", "public", "stem"):
        if key not in q.data:
            add(ERROR, f"field '{key}' is missing")
    if q.path is not None:
        if q.id and q.id != q.path.stem:
            add(ERROR, f"id '{q.id}' differs from the file name '{q.path.stem}'")
        if q.concept and q.concept != q.path.parent.name:
            add(ERROR, f"concept '{q.concept}' differs from the folder '{q.path.parent.name}'")
    if q.concept and s.concepts is not None and q.concept not in s.concepts:
        add(ERROR, f"concept '{q.concept}' is not listed in pool.toml")
    if "type" in q.data and q.type not in TYPES:
        add(ERROR, f"type '{q.type}' is not one of {', '.join(TYPES)}")
    if "level" in q.data and q.level not in LEVELS:
        add(ERROR, f"level '{q.level}' is not one of {', '.join(LEVELS)}")
    if "status" in q.data and q.status not in STATUSES:
        add(ERROR, f"status '{q.status}' is not one of {', '.join(STATUSES)}")
    if "public" in q.data and not isinstance(q.data["public"], bool):
        add(ERROR, "public must be true or false")

    if q.status == "retired":
        return out  # retired questions only need to stay readable

    missing = _texts(q.data.get("stem"), s.languages)
    if "stem" in q.data and missing:
        add(ERROR, f"question text missing in {', '.join(missing)}")

    image = q.get("image")
    if image and not any((pool.images_dir / f"{image}{ext}").exists() for ext in ("", ".svg", ".png")):
        add(ERROR, f"image '{image}' not found in images/")

    if q.type in ("single", "multiple"):
        _check_options(q, pool, add)
    elif q.type == "free_text":
        points = q.get("points")
        if not isinstance(points, (int, float)) or isinstance(points, bool) or points <= 0:
            add(ERROR, "free text needs points greater than 0")
        if "half_points" in q.data and not isinstance(q.get("half_points"), bool):
            add(ERROR, "half_points must be true or false")
        if missing := _texts(q.get("expected"), s.languages):
            add(WARNING, f"expected answer missing in {', '.join(missing)}")
    return out


def _check_options(q: Question, pool: Pool, add) -> None:
    s = pool.settings
    options = q.options
    if "options" not in q.data:
        add(ERROR, "field 'options' is missing")
        return
    if not (s.min_options <= len(options) <= s.max_options):
        add(ERROR, f"{len(options)} options, allowed are {s.min_options} to {s.max_options}")
    ids = [str(o.get("id")) for o in options if isinstance(o, dict)]
    if len(ids) != len(options):
        add(ERROR, "every option must be a mapping with id, correct, text and feedback")
        return
    if len(set(ids)) != len(ids):
        add(ERROR, "option ids are not unique")
    for o in options:
        oid = o.get("id")
        if not isinstance(o.get("correct"), bool):
            add(ERROR, f"option {oid}: correct must be true or false")
        if missing := _texts(o.get("text"), s.languages):
            add(ERROR, f"option {oid}: text missing in {', '.join(missing)}")
        if missing := _texts(o.get("feedback"), s.languages):
            add(WARNING, f"option {oid}: feedback missing in {', '.join(missing)}")

    n_correct = len(q.correct_ids)
    if q.type == "single" and n_correct != 1:
        add(ERROR, f"single choice needs exactly one correct option, has {n_correct}")
    if q.type == "multiple" and n_correct < 1:
        add(ERROR, "multiple choice needs at least one correct option")

    lang = s.languages[0]
    lengths = {str(o.get("id")): len(str((o.get("text") or {}).get(lang, ""))) for o in options}
    for oid, length in lengths.items():
        others = [v for k, v in lengths.items() if k != oid]
        if others and length >= LENGTH_MIN_CHARS and length > LENGTH_FACTOR * (sum(others) / len(others)):
            add(WARNING, f"option {oid} is much longer than the others and may give itself away")


def check_pool(pool: Pool) -> list[Finding]:
    questions, load_errors = pool.load()
    findings = [Finding(ERROR, e.path.stem, e.message, str(e.path)) for e in load_errors]
    for q in questions:
        findings.extend(check_question(q, pool))

    by_id: dict[str, list[Question]] = defaultdict(list)
    for q in questions:
        by_id[q.id].append(q)
    for qid, same in by_id.items():
        if qid and len(same) > 1:
            paths = ", ".join(str(q.path) for q in same)
            findings.append(Finding(ERROR, qid, f"id used by {len(same)} files: {paths}"))

    has_variant = {q.variant_of for q in questions if q.variant_of and q.status != "retired"}
    for q in questions:
        if q.status == "retired":
            continue
        if q.variant_of:
            original = by_id.get(q.variant_of)
            if not original:
                findings.append(Finding(ERROR, q.id, f"variant_of '{q.variant_of}' does not exist", str(q.path)))
            elif original[0].concept != q.concept:
                findings.append(Finding(ERROR, q.id, f"variant_of '{q.variant_of}' belongs to another concept", str(q.path)))
            if q.variant_of == q.id:
                findings.append(Finding(ERROR, q.id, "a question cannot be a variant of itself", str(q.path)))
            if q.public:
                findings.append(Finding(ERROR, q.id, "an exam variant must not be public", str(q.path)))
        elif q.public and q.type in ("single", "multiple") and q.id not in has_variant:
            findings.append(Finding(NOTE, q.id, "practice question without an exam variant", str(q.path)))

    known = set(pool.concepts())
    for concept in sorted(known - {q.concept for q in questions}):
        findings.append(Finding(NOTE, None, f"concept '{concept}' has no questions"))
    return findings


def summarize(findings: list[Finding]) -> dict[str, int]:
    counts = {ERROR: 0, WARNING: 0, NOTE: 0}
    for f in findings:
        counts[f.severity] += 1
    return counts
