"""The questions of one or more pools as rows for lists and searches, shared by the app window and the command line."""

from __future__ import annotations

import base64
from collections import defaultdict
from pathlib import Path
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from .checks import ERROR, NOTE, WARNING, Finding, check_pool, check_question
from .pool import Pool
from .question import Question


def plain(value):
    """A YAML value as plain Python data, for JSON."""
    if isinstance(value, (CommentedMap, dict)):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (CommentedSeq, list)):
        return [plain(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return str(value) if isinstance(value, str) else value
    return str(value)


def data_url(path: Path) -> str:
    """An image as a data URL, because the window cannot load files from the pool folder directly."""
    kind = {".svg": "svg+xml", ".jpg": "jpeg", ".jpeg": "jpeg"}.get(path.suffix.lower(), path.suffix.lower().lstrip("."))
    return f"data:image/{kind};base64," + base64.b64encode(path.read_bytes()).decode()


def _text(value, lang: str, fallback: list[str]) -> str:
    """A {lang: text} value in the wanted language, else in the first language that has it."""
    if not isinstance(value, dict):
        return str(value or "")
    for code in [lang, *fallback]:
        if str(value.get(code) or "").strip():
            return str(value[code])
    return ""


def _search_text(q: Question, *extra: str) -> str:
    parts = [q.id, q.concept, *extra]
    stem = q.get("stem")
    if isinstance(stem, dict):
        parts.extend(str(v) for v in stem.values())
    parts.append(str(q.get("code") or ""))
    parts.append(str(q.get("coverage") or ""))
    for option in q.options:
        if isinstance(option, dict):
            for key in ("text", "feedback"):
                if isinstance(option.get(key), dict):
                    parts.extend(str(v) for v in option[key].values())
    return " ".join(parts).lower()


def rows(pool: Pool, lang: str = "de") -> list[dict]:
    """One row per question of the pool, with its findings counted."""
    questions, load_errors = pool.load()
    findings = check_pool(pool, (questions, load_errors))
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {ERROR: 0, WARNING: 0, NOTE: 0})
    for f in findings:
        if f.question:
            counts[f.question][f.severity] += 1
    variants = defaultdict(list)
    for q in questions:
        if q.variant_of:
            variants[q.variant_of].append(q.id)
    languages = pool.settings.languages
    names = {c["id"]: c["name"] for c in pool.concept_info()}
    result = []
    for q in questions:
        result.append({
            "id": q.id,
            "pool": str(pool.root),
            "pool_name": pool.settings.name,
            "concept": q.concept,
            "concept_name": names.get(q.concept, q.concept),
            "type": q.type,
            "level": q.level,
            "status": q.status,
            "public": q.public,
            "exam": q.exam,
            "variant_of": q.variant_of,
            "modified": q.path.stat().st_mtime,
            "variants": variants.get(q.id, []),
            "stem": _text(q.get("stem"), lang, languages),
            "options": len(q.options),
            "errors": counts[q.id][ERROR],
            "warnings": counts[q.id][WARNING],
            "path": str(q.path),
            "search": _search_text(q, names.get(q.concept, "")),
        })
    for e in load_errors:
        result.append({
            "id": e.path.stem, "pool": str(pool.root), "pool_name": pool.settings.name,
            "concept": e.path.parent.name, "concept_name": e.path.parent.name, "type": "", "level": "", "status": "", "public": False, "exam": False,
            "modified": e.path.stat().st_mtime,
            "variant_of": None, "variants": [], "stem": "", "options": 0, "errors": 1, "warnings": 0,
            "path": str(e.path), "search": e.path.stem.lower(), "unreadable": e.message,
        })
    return result


def matches(row: dict, search: str) -> bool:
    """Every word of the search must occur somewhere in the question."""
    return all(word in row["search"] for word in search.lower().split())


def variant_findings(q: Question, pool: Pool) -> list[Finding]:
    """The checks of check_pool that concern a single exam variant, without reading the whole pool."""
    if not q.variant_of or q.status == "retired":
        return []
    out = []
    original = list(pool.questions_dir.glob(f"*/{q.variant_of}.yaml"))
    if not original:
        out.append(Finding(ERROR, q.id, f"variant_of '{q.variant_of}' does not exist", str(q.path),
                           "variant_missing", {"id": q.variant_of}))
    elif original[0].parent.name != q.concept:
        out.append(Finding(ERROR, q.id, f"variant_of '{q.variant_of}' belongs to another concept", str(q.path),
                           "variant_concept", {"id": q.variant_of}))
    if q.public:
        out.append(Finding(ERROR, q.id, "an exam variant must not be public", str(q.path), "variant_public"))
    return out


def detail(pool: Pool, qid: str) -> dict:
    """Everything about one question for the preview and the editor, with its findings and file time."""
    question = pool.find(qid)
    findings = [f.to_dict() for f in check_question(question, pool) + variant_findings(question, pool)]
    figures = []
    for name in question.images:
        found = pool.image_file(name)
        figures.append({"name": name, "data": data_url(found) if found else None})
    concept = next((c for c in pool.concept_info() if c["id"] == question.concept), None)
    return {
        "id": question.id,
        "concept_name": concept["name"] if concept else question.concept,
        "concept_description": concept["description"] if concept else "",
        "pool": str(pool.root),
        "pool_name": pool.settings.name,
        "languages": pool.settings.languages,
        "path": str(question.path),
        # As text: nanoseconds exceed the integers JavaScript can hold exactly.
        "mtime_ns": str(question.path.stat().st_mtime_ns),
        "modified": question.path.stat().st_mtime,
        "data": plain(question.data),
        "findings": findings,
        "figures": figures,
        "image_columns": question.image_columns,
    }
