"""Texts wrapped by hand become one line per paragraph, as Markdown reads them; structure stays."""

from __future__ import annotations

import hashlib
import tomllib

import tomli_w

from markwise import yamlio
from markwise.importer import import_pool, unwrap_pool
from markwise.pool import Pool
from markwise.text import unwrap, unwrap_question

from test_core import write_legacy


def test_lines_of_a_paragraph_are_joined_and_structure_stays():
    assert unwrap("Ein Team quittiert jede\nNachricht. Was\nunterscheidet das?\n") == "Ein Team quittiert jede Nachricht. Was unterscheidet das?"
    assert unwrap("Erster Absatz\ngeht weiter.\n\nZweiter.") == "Erster Absatz geht weiter.\n\nZweiter."
    assert unwrap("Welche?\n- eins\n  weiter\n- zwei") == "Welche?\n- eins weiter\n- zwei"
    assert unwrap("Gegeben:\n```\nx = 1\nprint(x)\n```\nDann\nweiter.") == "Gegeben:\n```\nx = 1\nprint(x)\n```\nDann weiter."
    assert unwrap("Zeile eins  \nZeile zwei") == "Zeile eins  \nZeile zwei"
    assert unwrap("Nur eine Zeile") == "Nur eine Zeile"


def test_a_question_is_unwrapped_in_place_and_a_single_paragraph_becomes_a_plain_line():
    data = yamlio._yaml().load(
        "stem:\n  de: |\n    Eins zwei\n    drei.\n  en: |\n    One.\n"
        "options:\n  - id: a\n    correct: true\n    text: {de: Ja, en: Yes}\n    feedback:\n      de: |\n        Weil\n        es so ist.\n")
    assert unwrap_question(data) == 2  # en "One." only loses its block, which is not counted
    text = yamlio.dumps(data)
    assert "de: Eins zwei drei." in text and "en: One." in text and "de: Weil es so ist." in text and "|" not in text
    assert unwrap_question(data) == 0


def test_the_import_unwraps_and_unwrapping_a_pool_keeps_the_import_state_true(tmp_path):
    legacy = write_legacy(tmp_path / "legacy")
    import_pool(legacy, tmp_path / "pool")
    pool = Pool.open(tmp_path / "pool")
    q = pool.find("co-001")
    q.data["stem"]["de"] = "Ein von Hand\numbrochener Text."  # as an import before this change left it
    q.save()
    state_path = pool.root / ".import.toml"
    state = tomllib.loads(state_path.read_text(encoding="utf-8"))
    state["questions"]["co-001"]["written"] = hashlib.sha256(q.path.read_bytes()).hexdigest()
    state_path.write_text(tomli_w.dumps(state), encoding="utf-8")

    assert unwrap_pool(pool)["questions"] == ["co-001"]  # counting changes nothing
    assert "\n" in pool.find("co-001").data["stem"]["de"]
    report = unwrap_pool(pool, write=True)
    assert report["questions"] == ["co-001"] and pool.find("co-001").data["stem"]["de"] == "Ein von Hand umbrochener Text."
    written = tomllib.loads(state_path.read_text(encoding="utf-8"))["questions"]["co-001"]["written"]
    assert written == hashlib.sha256(pool.find("co-001").path.read_bytes()).hexdigest()  # still counts as untouched
    assert import_pool(legacy, pool.root).unchanged.count("co-001") == 1
