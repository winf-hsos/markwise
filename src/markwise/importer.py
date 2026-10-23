"""Import a question bank in the earlier YAML format (German keys) into a Markwise pool.

The import never overwrites a question silently. It records a hash of every source file and of the file it
wrote in `.import.toml` inside the pool, so that a second run can tell new questions, unchanged ones, questions
that changed in the source, and questions that were edited in Markwise since the import apart.
"""

from __future__ import annotations

import hashlib
import re
import shutil
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import tomli_w
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from . import yamlio
from .pool import POOL_FILE, Pool, PoolSettings
from .question import ordered

STATE_FILE = ".import.toml"

KEYS = {
    "id": "id", "konzept": "concept", "niveau": "level", "status": "status", "oeffentlich": "public",
    "variante_von": "variant_of", "deckung": "coverage", "fehlvorstellung": "misconception",
    "sitzung": "session", "frage": "stem", "bild": "image", "code": "code",
}
LEVELS = {"erinnern": "remember", "verstehen": "understand", "anwenden": "apply"}
STATUSES = {"entwurf": "draft", "geprueft": "reviewed", "pilotiert": "piloted", "ausgemustert": "retired"}
OPTION_KEYS = {"kennung": "id", "text": "text", "begruendung": "feedback"}


@dataclass
class ImportReport:
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    changed_in_source: list[str] = field(default_factory=list)   # source changed, Markwise copy untouched
    conflicts: list[str] = field(default_factory=list)           # both changed, or a file of that id already exists
    images: list[str] = field(default_factory=list)
    concepts_named: list[str] = field(default_factory=list)  # concepts that got their name from a concept page
    problems: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _carry_comments(old: CommentedMap, new: CommentedMap, keys: dict) -> None:
    """Move the comments attached to the old keys over to the renamed keys."""
    for key, comment in old.ca.items.items():
        new_key = keys.get(key, key)
        if new_key in new:
            new.ca.items[new_key] = comment


def convert(old: CommentedMap) -> CommentedMap:
    """Map one question from the earlier format; fields without a mapping are kept under their names."""
    fields: dict = {}
    for key, value in old.items():
        if key in ("richtig", "optionen"):
            continue
        new_key = KEYS.get(key, key)
        if key == "niveau":
            value = LEVELS.get(value, value)
        elif key == "status":
            value = STATUSES.get(value, value)
        fields[new_key] = value

    correct = old.get("richtig")
    fields["type"] = "multiple" if isinstance(correct, list) else "single"
    correct_ids = {str(c) for c in correct} if isinstance(correct, list) else {str(correct)}

    options = []
    for old_option in old.get("optionen") or []:
        option = CommentedMap()
        option["id"] = old_option.get("kennung")
        option["correct"] = str(old_option.get("kennung")) in correct_ids
        for key, value in old_option.items():
            if key != "kennung":
                option[OPTION_KEYS.get(key, key)] = value
        _carry_comments(old_option, option, OPTION_KEYS)
        options.append(option)
    fields["options"] = options
    new = ordered(fields)
    _carry_comments(old, new, KEYS)
    return new


def _first_sentence(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # links keep their text
    text = re.sub(r"[*_`]", "", text).strip()
    match = re.match(r"(.+?[.!?])(\s|$)", text, re.S)
    return " ".join((match.group(1) if match else text).split())


def concept_pages(folder: Path) -> dict[str, dict]:
    """Name and short description of each concept page (Quarto .qmd): the title, and the subtitle or else the
    first sentence of the summary."""
    if not folder.is_dir():
        return {}
    result = {}
    for page in sorted(folder.glob("*.qmd")):
        if page.stem == "index":
            continue
        text = page.read_text(encoding="utf-8")
        meta, body = {}, text
        if text.startswith("---"):
            head, _, body = text[3:].partition("\n---")
            try:
                meta = YAML(typ="safe").load(head) or {}
            except Exception:
                meta = {}
        description = str(meta.get("subtitle") or "")
        if not description:
            summary = re.search(r"^##\s+(Summary|Zusammenfassung)\s*\n+(.+?)(\n\n|$)", body, re.M | re.S)
            if summary:
                description = _first_sentence(summary.group(2))
        result[page.stem] = {"name": str(meta.get("title") or ""), "description": description}
    return result


def _name_concepts(pool: Pool, pages: dict[str, dict]) -> list[str]:
    """Give concepts without a name the title of their page; names someone gave in Markwise stay."""
    named = []
    defined = pool.settings.concepts
    for cid in pool.concepts():
        page = pages.get(cid)
        if not page or not page.get("name"):
            continue
        info = (defined or {}).get(cid, {})
        if info.get("name"):
            continue
        pool.update_concept(cid, page["name"], info.get("description") or page.get("description", ""))
        defined = pool.settings.concepts
        named.append(cid)
    return named


def read_legacy_settings(legacy_toml: Path) -> dict:
    with open(legacy_toml, "rb") as f:
        return tomllib.load(f)


def import_pool(legacy_toml: Path | str, target: Path | str, update: bool = False) -> ImportReport:
    legacy_toml = Path(legacy_toml)
    target = Path(target)
    legacy = read_legacy_settings(legacy_toml)
    base = legacy_toml.parent
    questions_dir = base / legacy.get("fragen", "questions")
    images_dir = base / legacy.get("bilder", "diagrams")

    pages = concept_pages(base / legacy["konzepte"]) if legacy.get("konzepte") else {}
    if (target / POOL_FILE).exists():
        pool = Pool.open(target)
    else:
        concepts = pages or None
        pool = Pool.create(target, PoolSettings(
            name=legacy.get("name", base.name),
            languages=list(legacy.get("sprachen", ["de", "en"])),
            min_options=int(legacy.get("min_optionen", 4)),
            max_options=int(legacy.get("max_optionen", 5)),
            concepts=concepts,
        ))

    report_named = _name_concepts(pool, pages)

    state_path = pool.root / STATE_FILE
    state = tomllib.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    known = state.setdefault("questions", {})
    report = ImportReport()
    report.concepts_named = report_named
    images: set[str] = set()

    for source in sorted(questions_dir.glob("*/*.yaml")):
        try:
            old = yamlio.load(source)
        except Exception as exc:
            report.problems.append(f"{source.name}: cannot be read ({exc})")
            continue
        qid = str(old.get("id") or source.stem)
        concept = str(old.get("konzept") or source.parent.name)
        if old.get("bild"):
            images.add(str(old["bild"]))
        dest = pool.path_for(concept, qid)
        source_hash = _sha(source)
        record = known.get(qid)

        if record is None:
            if dest.exists():
                report.conflicts.append(qid)
                continue
            yamlio.dump(convert(old), dest)
            report.created.append(qid)
        elif record["source"] == source_hash:
            report.unchanged.append(qid)
            continue
        else:
            untouched = dest.exists() and _sha(dest) == record["written"]
            if not untouched:
                report.conflicts.append(qid)
                continue
            if not update:
                report.changed_in_source.append(qid)
                continue
            yamlio.dump(convert(old), dest)
            report.updated.append(qid)
        known[qid] = {"source": source_hash, "written": _sha(dest)}

    for name in sorted(images):
        found = [p for p in (images_dir / name, images_dir / f"{name}.svg", images_dir / f"{name}.png") if p.is_file()]
        if not found:
            report.problems.append(f"image '{name}' not found in the source")
        for path in found:
            copy = pool.images_dir / path.name
            if not copy.exists():
                pool.images_dir.mkdir(exist_ok=True)
                shutil.copy2(path, copy)
                report.images.append(path.name)

    state["source"] = str(legacy_toml.resolve())
    state_path.write_text(tomli_w.dumps(state), encoding="utf-8")
    return report
