"""Putting an exam together by hand, with invented questions only."""

from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest

from markwise import lifecycle
from markwise.app.api import Api
from markwise.exam import Exam, semester_of, suggest_points
from markwise.importer import import_pool
from markwise.module import Module
from markwise.pool import Pool

from test_core import write_legacy


@pytest.fixture
def module(tmp_path):
    import_pool(write_legacy(tmp_path / "legacy"), tmp_path / "pool")
    return Module.create(tmp_path / "module", "Invented Module", "IM", pools=[tmp_path / "pool"])


def test_points_follow_the_time_and_the_semester_the_date():
    assert [suggest_points(s) for s in (None, 15, 45, 60, 90, 120, 300)] == [1, 1, 1, 1, 1.5, 2, 5]
    assert semester_of(datetime.date(2027, 2, 5)) == "2026-27 - WS"
    assert semester_of(datetime.date(2026, 12, 10)) == "2026-27 - WS"
    assert semester_of(datetime.date(2026, 6, 1)) == "2026 - SS"


def test_an_exam_gets_its_folder_and_takes_questions_with_suggested_points(module):
    exam = Exam.create(module, "Probe: Klausur?", "2026-12-10", "en", "inline", author="")
    assert exam.root == module.root / "01 - Semester" / "2026-27 - WS" / "Exam" / "2026-12-10 - Probe Klausur"
    pool = module.open_pools()[0]
    q = pool.find("co-001")
    q.data["time_seconds"] = 90
    q.save()
    entry = exam.add(module, pool.root, "co-001")
    assert entry.points == 1.5 and entry.pool == module.pools[0]
    with pytest.raises(ValueError):
        exam.add(module, pool.root, "co-001")
    exam.add(module, pool.root, "co-002", points=3)
    exam.save()
    again = Exam.open(exam.root)
    assert [(q.id, q.points) for q in again.questions] == [("co-001", 1.5), ("co-002", 3.0)]
    assert again.language == "en" and again.answers == "inline" and again.total_points() == 4.5
    assert module.exams() == [exam.root]


def test_the_check_names_what_keeps_an_exam_from_printing(module):
    exam = Exam.create(module, "Check", "2027-01-21", "de", author="")
    pool = module.open_pools()[0]
    exam.add(module, pool.root, "co-001")  # practice question, parent of co-002
    exam.add(module, pool.root, "co-002")  # its exam variant
    codes = {f.code for f in exam.check(module)}
    assert {"exam_practice_only", "exam_same_family", "exam_examiners"} <= codes
    exam.language = "fr"
    assert "exam_language" in {f.code for f in exam.check(module)}
    lifecycle.retire(pool, "co-002")
    exam.language = "de"
    assert "exam_retired" in {f.code for f in exam.check(module)}


def test_the_api_creates_lists_and_changes_exams(module):
    api = Api()
    assert api.create_exam(str(module.root), {"title": "", "date": "2026-12-10"})["code"] == "exam_title_missing"
    detail = api.create_exam(str(module.root), {"title": "Probe", "date": "2026-12-10", "answers": "sheet"})["data"]
    pool = str(module.open_pools()[0].root.resolve())
    changed = api.update_exam(detail["path"], {"entries": [{"pool": pool, "id": "co-002", "points": 2},
                                                           {"pool": pool, "id": "co-001", "points": 1}],
                                               "examiners": ["Examiner A", " ", "Examiner B"]})["data"]
    assert [e["id"] for e in changed["entries"]] == ["co-002", "co-001"] and changed["points"] == 3
    assert changed["examiners"] == ["Examiner A", "Examiner B"]
    assert "exam_examiners" not in {f["code"] for f in changed["findings"]}
    assert api.list_exams(str(module.root))["data"][0]["questions"] == 2
    assert api.create_exam(str(module.root), {"title": "Probe", "date": "2026-12-10"})["code"] == "exam_exists"


def test_the_command_line_puts_an_exam_together(module, capsys):
    from markwise.cli import main
    assert main(["exam", "new", str(module.root), "--title", "Probe", "--date", "2026-12-10", "--json"]) == 0
    folder = json.loads(capsys.readouterr().out)["exam"]
    pool = str(module.open_pools()[0].root)
    assert main(["exam", "add", folder, pool, "co-002", "--points", "2"]) == 0
    capsys.readouterr()
    assert main(["exam", "show", folder, "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["points"] == 2 and report["questions"][0]["id"] == "co-002"
    assert main(["exam", "remove", folder, "co-002"]) == 0


def test_a_new_title_or_date_moves_the_folder_along(module):
    exam = Exam.create(module, "Mock", "2026-12-10", "en", author="")
    pool = module.open_pools()[0]
    exam.add(module, pool.root, "co-002")
    exam.save()
    (exam.root / "Print").mkdir()
    (exam.root / "Print" / "layout.json").write_text("{}", encoding="utf-8")
    api = Api()
    answer = api.update_exam(str(exam.root), {"title": "Mock exam: second try"})["data"]
    moved = module.root / "01 - Semester" / "2026-27 - WS" / "Exam" / "2026-12-10 - Mock exam second try"
    assert answer["path"] == str(moved) and answer["title"] == "Mock exam: second try"
    assert not exam.root.exists() and (moved / "Print" / "layout.json").exists()
    answer = api.update_exam(answer["path"], {"date": "2027-05-04"})["data"]
    assert answer["semester"] == "2027 - SS" and "2027 - SS" in answer["path"]
    again = Exam.open(answer["path"])
    assert again.title == "Mock exam: second try" and [q.id for q in again.questions] == ["co-002"]
    assert again.check(module) and not any(f.code == "exam_pool_missing" for f in again.check(module))
    Exam.create(module, "Other", "2027-05-04", "en", author="")
    refused = api.update_exam(answer["path"], {"title": "Other"})
    assert refused["code"] == "exam_exists" and Path(answer["path"]).exists()
    assert api.update_exam(answer["path"], {"title": "  "})["code"] == "exam_title_missing"


def test_sections_start_before_a_question_and_follow_it_when_the_order_changes(module):
    from markwise.exam import ExamSection
    exam = Exam.create(module, "Parts", "2027-01-21", "en", author="")
    pool = module.open_pools()[0]
    exam.add(module, pool.root, "co-001")
    exam.add(module, pool.root, "co-002", points=3)
    a, b = ExamSection("s1", "Part A", "Tick one box."), ExamSection("s2", "Part B")
    exam.set_flat([a, exam.questions[0], b, exam.questions[1]])
    exam.save()
    again = Exam.open(exam.root)
    assert [(s.id, s.title, s.note, s.before) for s in again.sections] == [("s1", "Part A", "Tick one box.", 0), ("s2", "Part B", "", 1)]
    assert [getattr(i, "title", None) or i.id for i in again.flat()] == ["Part A", "co-001", "Part B", "co-002"]
    assert again.section_points(again.sections[1]) == 3 and again.new_section_id() == "s3"
    # the interface sends the exam as one list; moving a question across a heading moves it into the other part
    api = Api()
    entries = api.get_exam(str(exam.root))["data"]["entries"]
    assert [e.get("section") or e["id"] for e in entries] == ["s1", "co-001", "s2", "co-002"]
    entries = [entries[0], entries[1], entries[3], entries[2], {"section": "", "title": "", "note": ""}]
    answer = api.update_exam(str(exam.root), {"entries": entries})["data"]
    assert [e.get("section") or e["id"] for e in answer["entries"]] == ["s1", "co-001", "co-002", "s2", "s3"]
    codes = {(f["code"], f["params"].get("section")) for f in answer["findings"]}
    assert {("exam_section_empty", "s2"), ("exam_section_empty", "s3"), ("exam_section_title", "s3")} <= codes


def test_a_section_about_one_concept_points_out_questions_about_another(module):
    from markwise.exam import ExamSection
    exam = Exam.create(module, "Topics", "2027-01-21", "en", author="")
    pool = module.open_pools()[0]
    q = pool.new_question("shapes", "single", author="")
    exam.add(module, pool.root, "co-001")
    exam.add(module, pool.root, q.id)
    exam.set_flat([ExamSection("s1", "Colours", pool=module.pools[0], concept="colours"), *exam.questions])
    exam.save()
    again = Exam.open(exam.root)
    assert (again.sections[0].pool, again.sections[0].concept) == (module.pools[0], "colours")
    found = [(f.code, f.question) for f in again.check(module) if f.code == "exam_section_concept"]
    assert found == [("exam_section_concept", q.id)]
    entry = Api().get_exam(str(exam.root))["data"]["entries"][0]
    assert entry["concept"] == "colours" and entry["pool"] == str(pool.root)
    entry["concept"] = ""
    rest = Api().get_exam(str(exam.root))["data"]["entries"][1:]
    Api().update_exam(str(exam.root), {"entries": [entry, *rest]})
    assert Exam.open(exam.root).sections[0].concept == ""
