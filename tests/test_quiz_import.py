"""Quizzes of the Hands-on Computer Science platform into a pool, with invented questions only."""

from __future__ import annotations

from pathlib import Path

from markwise.booklet import item_of
from markwise.checks import ERROR, NOTE, check_pool
from markwise.cli import main
from markwise.exam import Exam
from markwise.module import Module
from markwise.pool import Pool, PoolSettings
from markwise.quiz_import import import_quiz, parse_quiz

EN = """\
---
type: quiz
code: 1234
title: "Quiz: colours"
status: published
---

## Which colour is the sky? {#co-001}

- [x] Blue.
  > Right: light is scattered.
- [ ] Green.
  > No: that is grass.
- [ ] Red.
  > Only at sunset.
- [ ] Yellow.
  > That is the sun.

> The sky is blue because blue light is scattered most.

## Which are colours? (Several answers may be correct.) {#co-002}

- [x] Red
  > Yes.
- [ ] Loud
  > A sound.
- [ ] Heavy
  > A weight.
- [ ] Fast
  > A speed.

## What does this program print?

```python static
print("cold")
```

- [x] `cold`
- [ ] `hot`
  > The text in the brackets is printed as it is.
- [ ] nothing

> `print` shows exactly the text it is given.
"""

DE = """\
---
title: "Quiz: Farben"
translation_of: en
---

## Welche Farbe hat der Himmel? {#co-001}

- [x] Blau.
  > Richtig: Licht wird gestreut.
- [ ] Grün.
  > Nein: Das ist Gras.
- [ ] Rot.
  > Nur bei Sonnenuntergang.
- [ ] Gelb.
  > Das ist die Sonne.

> Der Himmel ist blau, weil blaues Licht am stärksten
> gestreut wird.

## Welche sind Farben? (Mehrere richtige Antworten möglich.) {#co-002}

- [x] Rot
  > Ja.
- [ ] Laut
  > Ein Klang.
- [ ] Schwer
  > Ein Gewicht.
- [ ] Schnell
  > Eine Geschwindigkeit.

## Was gibt dieses Programm aus?

```python static
print("kalt")
```

- [x] `kalt`
- [ ] `heiß`
  > Der Text in den Klammern wird so ausgegeben, wie er dasteht.
- [ ] nichts

> `print` zeigt genau den Text, den es bekommt.
"""


def write_quiz(folder: Path) -> Path:
    folder.mkdir(parents=True)
    (folder / "en.md").write_text(EN, encoding="utf-8")
    (folder / "de.md").write_text(DE, encoding="utf-8")
    return folder


def test_parse_reads_ids_hints_code_feedback_and_takeaway(tmp_path):
    meta, questions = parse_quiz(write_quiz(tmp_path / "colours-quiz") / "de.md")
    assert meta["title"] == "Quiz: Farben"
    first, several, program = questions
    assert first.id == "co-001" and first.stem == "Welche Farbe hat der Himmel?"
    assert first.takeaway == "Der Himmel ist blau, weil blaues Licht am stärksten gestreut wird."
    assert [o["correct"] for o in first.options] == [True, False, False, False]
    assert first.options[1]["feedback"] == "Nein: Das ist Gras."
    assert several.several and several.stem == "Welche sind Farben?"
    assert program.id is None and program.code == 'print("kalt")' and program.code_language == "python"
    assert program.options[0]["feedback"] == "" and program.options[1]["feedback"].startswith("Der Text")


def test_import_joins_the_languages_and_never_imports_twice(tmp_path):
    quiz = write_quiz(tmp_path / "colours-quiz")
    pool = Pool.create(tmp_path / "pool", PoolSettings(name="Invented Science", id_prefix="inv"))
    report = import_quiz(pool, quiz, levels={"co-001": "remember"})
    assert report.created == ["co-001", "co-002", "inv-001"] and report.quiz_status == "published"
    assert pool.settings.concepts["colours"]["name"] == "colours"

    sky = pool.find("co-001")
    assert sky.type == "single" and sky.level == "remember" and sky.status == "draft" and sky.public
    assert sky.get("takeaway")["en"].startswith("The sky is blue")
    several = pool.find("co-002")
    assert several.type == "multiple" and several.get("time_seconds") == 90 and several.level == "understand"
    program = pool.find("inv-001")
    assert program.level == "apply" and program.get("code") == {"de": 'print("kalt")\n', "en": 'print("cold")\n'}
    assert "feedback" not in program.options[0]

    findings = check_pool(pool)
    assert [f for f in findings if f.severity == ERROR] == []
    assert any(f.code == "option_count_practice" and f.question == "inv-001" for f in findings)

    again = import_quiz(pool, quiz)
    assert again.created == [] and again.existing == ["co-001", "co-002", "question 3"]


def test_three_options_are_enough_for_practice_but_not_for_an_exam(tmp_path):
    pool = Pool.create(tmp_path / "pool", PoolSettings(name="Invented Science", id_prefix="inv"))
    import_quiz(pool, write_quiz(tmp_path / "colours-quiz"))
    program = pool.find("inv-001")
    program.data["exam"] = True
    program.save()
    assert any(f.code == "option_count" and f.severity == ERROR for f in check_pool(pool) if f.question == "inv-001")

    program.data["exam"] = False
    program.save()
    module = Module.create(tmp_path / "module", "Invented Module", "IM", pools=[pool.root])
    exam = Exam.create(module, "Exam", "2027-02-05", "de", author="")
    exam.add(module, pool.root, "inv-001", points=1)
    found = {f.code for f in exam.check(module)}
    assert "exam_few_options" in found


def test_the_booklet_takes_the_code_of_its_language(tmp_path):
    pool = Pool.create(tmp_path / "pool", PoolSettings(name="Invented Science", id_prefix="inv"))
    import_quiz(pool, write_quiz(tmp_path / "colours-quiz"))
    assert item_of(pool, "inv-001", "de").code == 'print("kalt")\n'
    assert item_of(pool, "inv-001", "en").code == 'print("cold")\n'


def test_cli_imports_quizzes_into_a_pool_with_its_prefix(tmp_path, capsys):
    quiz = write_quiz(tmp_path / "colours-quiz")
    assert main(["pool", "init", str(tmp_path / "pool"), "--name", "Invented Science", "--prefix", "inv"]) == 0
    assert main(["import-quiz", str(tmp_path / "pool"), str(quiz), "--name", "Colours"]) == 0
    assert "colours (quiz published): 3 created" in capsys.readouterr().out
    pool = Pool.open(tmp_path / "pool")
    assert pool.settings.id_prefix == "inv" and pool.settings.concepts["colours"]["name"] == "Colours"
