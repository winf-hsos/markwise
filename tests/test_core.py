"""Question pools, checks, import and modules, with invented questions only."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from markwise import yamlio
from markwise.checks import ERROR, NOTE, WARNING, check_pool
from markwise.cli import main
from markwise.importer import import_pool
from markwise.module import Module
from markwise.pool import Pool, PoolSettings
from markwise.question import ConflictError, Question

LEGACY_TOML = """\
name = "Invented Course"
fragen = "questions"
konzepte = "concepts"
bilder = "diagrams"
sprachen = ["de", "en"]
min_optionen = 4
max_optionen = 5
"""

LEGACY_QUESTION = """\
id: {qid}
konzept: colours
sitzung: 3
niveau: verstehen
status: entwurf
oeffentlich: {public}
{variant}deckung: "Deck 01"
experiment: lab-2   # a field the schema does not know
frage:
  de: |
    Welche Farbe hat der Himmel?
  en: |
    What colour is the sky?
bild: sky
richtig: {correct}
optionen:
  - kennung: a
    text:        {{de: "Blau", en: "Blue"}}
    begruendung: {{de: "Ja.", en: "Yes."}}
  - kennung: b
    text:        {{de: "Grün", en: "Green"}}
    begruendung: {{de: "Nein.", en: "No."}}
  - kennung: c
    text:        {{de: "Rot", en: "Red"}}
    begruendung: {{de: "Nein.", en: "No."}}
  - kennung: d
    text:        {{de: "Gelb", en: "Yellow"}}
    begruendung: {{de: "Nein.", en: "No."}}
"""


def write_legacy(root: Path) -> Path:
    (root / "concepts").mkdir(parents=True)
    pages = {
        "colours": '---\ntitle: "Colours of Things"\nlang: en\n---\n\n## Summary\n\nColour is light we see. It has [three](x.html) parts.\n',
        "shapes": '---\ntitle: "Shapes"\nsubtitle: "Round, square and in between"\n---\n\nText.\n',
        "index": "",
    }
    for name, text in pages.items():
        (root / "concepts" / f"{name}.qmd").write_text(text, encoding="utf-8")
    (root / "diagrams").mkdir()
    (root / "diagrams" / "sky.svg").write_text("<svg/>", encoding="utf-8")
    folder = root / "questions" / "colours"
    folder.mkdir(parents=True)
    (folder / "co-001.yaml").write_text(
        LEGACY_QUESTION.format(qid="co-001", public="true", variant="", correct="a"), encoding="utf-8")
    (folder / "co-002.yaml").write_text(
        LEGACY_QUESTION.format(qid="co-002", public="false", variant="variante_von: co-001\n", correct="[a, b]"),
        encoding="utf-8")
    (root / "pool.toml").write_text(LEGACY_TOML, encoding="utf-8")
    return root / "pool.toml"


@pytest.fixture
def imported(tmp_path) -> tuple[Path, Pool]:
    legacy = write_legacy(tmp_path / "legacy")
    import_pool(legacy, tmp_path / "pool")
    return legacy, Pool.open(tmp_path / "pool")


# --- import ---------------------------------------------------------------------------


def test_import_converts_keys_and_values(imported):
    _, pool = imported
    assert pool.settings.name == "Invented Course"
    assert list(pool.settings.concepts) == ["colours", "shapes"]
    assert pool.settings.concepts["colours"] == {"name": "Colours of Things", "description": "Colour is light we see."}
    assert pool.settings.concepts["shapes"]["description"] == "Round, square and in between"
    single = pool.find("co-001")
    assert single.type == "single" and single.level == "understand" and single.status == "draft"
    assert single.public and single.correct_ids == ["a"]
    assert single.get("coverage") == "Deck 01" and single.get("session") == 3
    assert single.get("experiment") == "lab-2"
    assert single.options[0]["feedback"]["en"] == "Yes."
    variant = pool.find("co-002")
    assert variant.type == "multiple" and variant.correct_ids == ["a", "b"] and variant.variant_of == "co-001"
    assert (pool.images_dir / "sky.svg").exists()
    text = single.path.read_text(encoding="utf-8")
    assert "# a field the schema does not know" in text
    assert list(single.data.keys())[:6] == ["id", "concept", "type", "level", "status", "public"]


def test_imported_pool_passes_the_checks(imported):
    _, pool = imported
    findings = check_pool(pool)
    assert [f for f in findings if f.severity in (ERROR, WARNING)] == []
    assert any(f.severity == NOTE and "shapes" in f.message for f in findings)


def test_reimport_never_overwrites_silently(imported, tmp_path):
    legacy, pool = imported
    assert import_pool(legacy, pool.root).unchanged == ["co-001", "co-002"]

    source = legacy.parent / "questions" / "colours" / "co-001.yaml"
    source.write_text(source.read_text(encoding="utf-8").replace("Blau", "Hellblau"), encoding="utf-8")
    report = import_pool(legacy, pool.root)
    assert report.changed_in_source == ["co-001"]
    assert pool.find("co-001").options[0]["text"]["de"] == "Blau"

    report = import_pool(legacy, pool.root, update=True)
    assert report.updated == ["co-001"]
    assert pool.find("co-001").options[0]["text"]["de"] == "Hellblau"

    # Edited in Markwise and in the source: a conflict, nothing is overwritten.
    q = pool.find("co-001")
    q.data["level"] = "apply"
    q.save()
    source.write_text(source.read_text(encoding="utf-8").replace("Hellblau", "Dunkelblau"), encoding="utf-8")
    report = import_pool(legacy, pool.root, update=True)
    assert report.conflicts == ["co-001"]
    assert pool.find("co-001").level == "apply"


# --- checks ---------------------------------------------------------------------------


def messages(pool: Pool, qid: str) -> list[str]:
    return [f.message for f in check_pool(pool) if f.question == qid and f.severity == ERROR]


def test_checks_find_broken_questions(imported):
    _, pool = imported
    q = pool.find("co-001")
    q.data["options"][1]["correct"] = True          # single choice with two correct options
    q.data["options"].pop()                         # only three options left
    q.data["stem"]["en"] = ""                       # a language missing
    q.save()
    v = pool.find("co-002")
    v.data["public"] = True                         # an exam variant must not be public
    v.data["id"] = "co-099"                         # differs from the file name
    v.save()
    found = " | ".join(messages(pool, "co-001") + messages(pool, "co-099"))
    assert "exactly one correct option, has 2" in found
    assert "3 options" in found
    assert "question text missing in en" in found
    assert "must not be public" in found
    assert "differs from the file name" in found


def test_long_option_gives_itself_away(imported):
    _, pool = imported
    q = pool.find("co-001")
    q.data["options"][0]["text"]["de"] = "Blau, weil das Sonnenlicht an den Molekülen der Luft gestreut wird"
    q.save()
    warnings = [f for f in check_pool(pool) if f.severity == WARNING]
    assert any("option a is much longer" in f.message for f in warnings)


def test_retired_questions_are_only_read(imported):
    _, pool = imported
    q = pool.find("co-001")
    q.data["status"] = "retired"
    q.data["options"] = []
    q.save()
    assert messages(pool, "co-001") == []


# --- pool -----------------------------------------------------------------------------


def test_new_question_and_delete(imported):
    _, pool = imported
    q = pool.new_question("colours", "single")
    assert q.id == "co-003" and len(q.options) == 4 and q.path.exists()
    free = pool.new_question("shapes", "free_text")
    assert free.id == "s-001" and free.get("points") == 2
    assert pool.delete("co-003", used_in_exam=False) == "deleted"
    assert pool.delete("co-001", used_in_exam=True) == "retired"
    assert pool.find("co-001").status == "retired"
    assert pool.next_id("co") == "co-003"  # a deleted draft frees its id; retired questions keep theirs


def test_save_detects_a_change_on_disk(imported):
    _, pool = imported
    mine = pool.find("co-001")
    theirs = pool.find("co-001")
    theirs.data["level"] = "apply"
    theirs.save()
    os.utime(theirs.path, ns=(mine._mtime_ns + 10_000_000, mine._mtime_ns + 10_000_000))
    mine.data["level"] = "remember"
    with pytest.raises(ConflictError):
        mine.save()
    mine.save(force=True)
    assert pool.find("co-001").level == "remember"


def test_round_trip_keeps_untouched_text(imported):
    _, pool = imported
    q = pool.find("co-001")
    before = q.path.read_text(encoding="utf-8")
    Question.load(q.path).save(force=True)
    assert q.path.read_text(encoding="utf-8") == before


# --- module ---------------------------------------------------------------------------


def test_module_points_to_its_pools_and_finds_exams(imported, tmp_path):
    _, pool = imported
    module = Module.create(tmp_path / "module", "Invented Module", "IM", pools=[pool.root])
    reopened = Module.open(tmp_path / "module")
    assert reopened.pools == ["../pool"]
    assert reopened.open_pools()[0].settings.name == "Invented Course"
    exam = reopened.new_exam_folder("2026-27 - WS", "2027-02-05", "Exam")
    exam.mkdir(parents=True)
    (exam / "exam.toml").write_text("", encoding="utf-8")
    assert reopened.exams() == [exam]


# --- command line ---------------------------------------------------------------------


def test_cli_check_and_list_in_json(imported, capsys):
    _, pool = imported
    assert main(["check", str(pool.root), "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["counts"]["error"] == 0
    assert main(["question", "list", str(pool.root), "--public", "no", "--json"]) == 0
    listed = json.loads(capsys.readouterr().out)
    assert [q["id"] for q in listed] == ["co-002"]


def test_cli_delete_needs_confirmation(imported):
    _, pool = imported
    assert main(["question", "delete", str(pool.root), "co-001"]) == 2
    assert pool.find("co-001").status == "draft"


def test_pool_refuses_fewer_than_four_options(tmp_path):
    with pytest.raises(ValueError):
        Pool.create(tmp_path / "p", PoolSettings(name="x", min_options=3))
