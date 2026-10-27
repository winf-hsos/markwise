"""Changing a question from the window or the command line without disturbing the rest of its file.

Changes arrive as plain data (what the editor shows). They are merged into the YAML mapping in place: values
that did not change keep their objects and thus their quoting and block style, options are matched by their
id, and fields the editor does not handle (unknown fields, comments) are never touched.
"""

from __future__ import annotations

import json
from pathlib import Path

from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import LiteralScalarString

from .catalog import plain, variant_findings
from .checks import Finding, check_question
from .pool import Pool
from .question import FIELD_ORDER, INHERITED, ConflictError, Question, default_author, insert_field, today

# Fields the editor owns. id and concept name the file, status and reviewed_by belong to the release, and
# the authorship fields are written by Markwise itself.
EDITABLE = tuple(k for k in FIELD_ORDER if k not in ("id", "concept", "status", "reviewed_by", "created_by",
                                                     "created_at", "changed_by", "changed_at"))
OPTION_KEYS = ("id", "correct", "text", "feedback")
# Fields that disappear from the file when the editor leaves them empty; all others always stay.
OPTIONAL = ("variant_of", "coverage", "misconception", "session", "image", "images", "image_columns", "code",
            "code_language", "time_seconds")


def _empty(value) -> bool:
    if value is None or value == "":
        return True
    if isinstance(value, dict):
        return all(_empty(v) for v in value.values())
    if isinstance(value, list):
        return not value
    return False


def _string(old, new: str):
    """New text in the style of the old value: a block for several lines, the old quoting otherwise."""
    if isinstance(old, str) and old == new:
        return old
    if "\n" in new or "\\" in new:
        # Several lines, or a backslash (LaTeX in a formula): a block shows the text exactly as typed, where
        # quotes would double every backslash.
        return LiteralScalarString(new)
    if isinstance(old, str) and type(old) is not str and not isinstance(old, LiteralScalarString):
        return type(old)(new)  # keeps double or single quotes
    return new


def _merge(old, new):
    if isinstance(new, dict):
        target = old if isinstance(old, CommentedMap) else CommentedMap()
        if not isinstance(old, CommentedMap) and all(isinstance(v, str) and "\n" not in v for v in new.values()):
            target.fa.set_flow_style()  # short {de: …, en: …} maps stay on one line, as in the template
        for key, value in new.items():
            target[key] = _merge(target.get(key), value)
        return target  # keys only in the old map (another language, say) are kept
    if isinstance(new, str):
        return _string(old, new)
    return new


def _merge_options(old: list | None, new: list[dict]) -> list:
    by_id = {str(o.get("id")): o for o in (old or []) if isinstance(o, dict)}
    result = []
    for option in new:
        existing = by_id.get(str(option.get("id")))
        merged = existing if existing is not None else CommentedMap()
        for key in OPTION_KEYS:
            if key in option:
                merged[key] = _merge(merged.get(key), option[key])
        result.append(merged)
    if old is not None and hasattr(old, "clear"):
        old.clear()  # keep the sequence object, so that its comments and indentation stay
        old.extend(result)
        return old
    return result


def _figures(fields: dict) -> dict:
    """Figures in their shortest form: one figure as `image`, several as `images` with `image_columns`."""
    if "images" not in fields:
        return fields
    fields = dict(fields)
    names = [n for n in fields.pop("images") or [] if n]
    columns = fields.pop("image_columns", 1) or 1
    if len(names) <= 1:
        fields.update(image=names[0] if names else "", images=[], image_columns=None)
    else:
        fields.update(image="", images=names, image_columns=columns if columns > 1 else None)
    return fields


def apply(data: CommentedMap, fields: dict) -> bool:
    """Merge the editor's fields into the mapping; returns whether anything changed."""
    fields = _figures(fields)
    changed = False
    variant = bool(fields.get("variant_of", data.get("variant_of")))
    for key in EDITABLE:
        if key not in fields:
            continue
        value = fields[key]
        if variant and key in INHERITED and _empty(value):
            if key in data:  # the variant takes this setting from its parent again
                del data[key]
                changed = True
            continue
        if key == "exam":
            # Written only where it differs from its default (exam questions are those not public), so that
            # files keep their shape until a question is meant for both.
            public = fields.get("public", data.get("public") is True)
            if value == (not public):
                if "exam" in data:
                    del data["exam"]
                    changed = True
                continue
        if key in OPTIONAL and _empty(value):
            if key in data:  # the editor emptied an optional field
                del data[key]
                changed = True
            continue
        if plain(data.get(key)) == plain(value):
            continue
        changed = True
        if key == "options":
            data[key] = _merge_options(data.get(key), value)
        elif key in data:
            data[key] = _merge(data[key], value)
        else:
            insert_field(data, key, _merge(None, value))
    return changed


def check_fields(pool: Pool, qid: str, fields: dict) -> list[dict]:
    """The findings the question would have with these fields, before anything is saved."""
    original = pool.find(qid)
    data = dict(plain(original.data))
    for key in EDITABLE:
        if key in fields:
            data[key] = fields[key]
    if data.get("variant_of"):
        for key in INHERITED:
            if key in data and _empty(data[key]):
                del data[key]  # left empty in the editor: inherited, not missing
    draft = pool.attach_parent(Question(data, original.path))
    findings: list[Finding] = check_question(draft, pool) + variant_findings(draft, pool)
    return [f.to_dict() for f in findings]


def save(pool: Pool, qid: str, fields: dict, expected_mtime_ns: int | None = None,
         force: bool = False, author: str | None = None) -> tuple[Question, bool]:
    """Save the editor's fields. Every change records who made it and when; a release stays, also when the
    content changes (Nicolas, 2026-10-27), and is taken back only by the examiner who gave it."""
    question = pool.find(qid)
    if not force and expected_mtime_ns is not None and question.path.stat().st_mtime_ns != expected_mtime_ns:
        raise ConflictError(f"{question.path} changed on disk since it was opened")
    changed = apply(question.data, fields)
    if changed:
        author = default_author() if author is None else author
        if author:
            for key, value in (("changed_by", author), ("changed_at", today())):
                if key in question.data:
                    question.data[key] = value
                else:
                    insert_field(question.data, key, value)
        question.save(force=True)
    return question, changed


def set_field(pool: Pool, qid: str, path: str, raw_value: str) -> tuple[Question, bool]:
    """Change one field by a dotted path such as `level`, `stem.de` or `options.b.correct`."""
    question = pool.find(qid)
    fields = {k: plain(question.data[k]) for k in EDITABLE if k in question.data}
    try:
        value = json.loads(raw_value)  # true, false, numbers, lists
    except json.JSONDecodeError:
        value = raw_value
    parts = path.split(".")
    if parts[0] not in EDITABLE:
        raise ValueError(f"'{parts[0]}' cannot be changed here (editable: {', '.join(EDITABLE)})")
    if len(parts) == 1:
        fields[parts[0]] = value
    elif parts[0] == "options":
        option = next((o for o in fields.get("options", []) if str(o.get("id")) == parts[1]), None)
        if option is None:
            raise ValueError(f"no option '{parts[1]}'")
        target = option
        for part in parts[2:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = value
    else:
        target = fields.setdefault(parts[0], {})
        for part in parts[1:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = value
    return save(pool, qid, fields)


def mtime_ns(path: str | Path) -> int:
    return Path(path).stat().st_mtime_ns
