"""Release, exam variants, retiring and taking back, with invented questions only."""

from __future__ import annotations

import pytest

from markwise import catalog, editing, lifecycle
from markwise.checks import check_pool
from markwise.question import INHERITED
from markwise.app.api import Api
from markwise.importer import import_pool
from markwise.pool import Pool

from test_core import write_legacy


@pytest.fixture
def pool(tmp_path):
    import_pool(write_legacy(tmp_path / "legacy"), tmp_path / "pool")
    return Pool.open(tmp_path / "pool")


def test_two_examiners_release_and_withdraw(pool):
    q = lifecycle.release(pool, "co-001", "Examiner A")
    assert q.status == "reviewed" and list(q.data["reviewed_by"]) == ["Examiner A"]
    q = lifecycle.release(pool, "co-001", "Examiner B")
    assert list(q.data["reviewed_by"]) == ["Examiner A", "Examiner B"]
    assert list(lifecycle.release(pool, "co-001", "Examiner B").data["reviewed_by"]) == ["Examiner A", "Examiner B"]
    q = lifecycle.withdraw(pool, "co-001", "Examiner A")
    assert q.status == "reviewed" and list(q.data["reviewed_by"]) == ["Examiner B"]
    q = lifecycle.withdraw(pool, "co-001", "Examiner B")
    assert q.status == "draft" and "reviewed_by" not in q.data
    with pytest.raises(lifecycle.LifecycleError):
        lifecycle.withdraw(pool, "co-001", "Examiner B")


def test_release_is_no_change_of_content(pool):
    q = lifecycle.release(pool, "co-001", "Examiner A")
    assert "changed_by" not in q.data and list(q.data.keys()).index("reviewed_by") > list(q.data.keys()).index("public")


def test_a_question_with_errors_cannot_be_released(pool):
    q = pool.find("co-001")
    q.data["options"][1]["correct"] = True
    q.save()
    with pytest.raises(lifecycle.LifecycleError) as caught:
        lifecycle.release(pool, "co-001", "Examiner A")
    assert caught.value.code == "has_errors"


def test_releasing_needs_a_name(pool, monkeypatch):
    monkeypatch.delenv("USERNAME", raising=False)
    monkeypatch.delenv("USER", raising=False)
    with pytest.raises(lifecycle.LifecycleError) as caught:
        lifecycle.release(pool, "co-001")
    assert caught.value.code == "name_missing"


def test_exam_variant_starts_as_a_copy(pool):
    lifecycle.release(pool, "co-001", "Examiner A")
    variant = lifecycle.create_variant(pool, "co-001", "Examiner B")
    assert variant.id == "co-001-v1" and variant.variant_of == "co-001" and not variant.public and variant.exam
    assert variant.status == "draft" and "reviewed_by" not in variant.data and variant.get("created_by") == "Examiner B"
    assert variant.data["stem"]["en"] == pool.find("co-001").data["stem"]["en"]
    assert variant.path == pool.path_for("colours", "co-001-v1")
    assert lifecycle.create_variant(pool, "co-001", "Examiner B").id == "co-001-v2"
    assert pool.next_id(pool.prefix_for("colours")) == "co-003"  # variants do not disturb the numbering
    with pytest.raises(lifecycle.LifecycleError):
        lifecycle.create_variant(pool, "co-002")  # co-002 is a variant itself


def test_retire_and_take_back(pool):
    lifecycle.release(pool, "co-001", "Examiner A")
    assert lifecycle.retire(pool, "co-001").status == "retired"
    q = lifecycle.restore(pool, "co-001")
    assert q.status == "draft" and "reviewed_by" not in q.data
    with pytest.raises(lifecycle.LifecycleError):
        lifecycle.restore(pool, "co-001")


def test_api_steps_answer_with_the_question_or_a_code(pool, monkeypatch):
    monkeypatch.setenv("USERNAME", "examiner-a")
    api = Api()
    assert api.whoami()["data"] == "examiner-a"
    assert api.release_question(str(pool.root), "co-001")["data"]["data"]["reviewed_by"] == ["examiner-a"]
    assert api.create_variant(str(pool.root), "co-002")["code"] == "not_practice"
    variant = api.create_variant(str(pool.root), "co-001")["data"]
    assert api.delete_question(str(pool.root), variant["id"])["data"]["outcome"] == "deleted"
    assert api.delete_question(str(pool.root), "co-001")["data"]["outcome"] == "retired"  # reviewed: only retired


def test_cli_release_and_variant(pool, capsys, monkeypatch):
    import json
    from markwise.cli import main
    assert main(["question", "release", str(pool.root), "co-001", "--by", "Examiner A", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["reviewed_by"] == ["Examiner A"]
    assert main(["question", "variant", str(pool.root), "co-001", "--by", "Examiner A", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["id"] == "co-001-v1"
    assert main(["question", "retire", str(pool.root), "co-001-v1"]) == 0
    assert pool.find("co-001-v1").status == "retired"


def test_a_variant_inherits_the_settings_of_its_parent_until_it_sets_its_own(pool):
    variant = lifecycle.create_variant(pool, "co-001", "Examiner B")
    for key in INHERITED:
        assert key not in variant.data  # only texts are copied
    parent = pool.find("co-001")
    loaded = pool.find(variant.id)
    assert loaded.level == parent.level and loaded.type == parent.type
    assert loaded.get("time_seconds") == parent.get("time_seconds")
    assert set(loaded.inherited()) >= {"type", "level"}

    parent.data["level"] = "apply"
    parent.save()
    assert pool.find(variant.id).level == "apply"  # a change at the parent reaches the variant
    row = next(r for r in catalog.rows(pool) if r["id"] == variant.id)
    assert row["level"] == "apply" and row["errors"] == 0

    editing.save(pool, variant.id, {"level": "remember"}, author="")
    assert pool.find(variant.id).data["level"] == "remember"  # its own value now
    parent.data["level"] = "understand"
    parent.save()
    assert pool.find(variant.id).level == "remember"
    editing.save(pool, variant.id, {"level": None}, author="")
    again = pool.find(variant.id)
    assert "level" not in again.data and again.level == "understand"  # inherits again


def test_an_orphaned_variant_reports_what_it_lacks(pool):
    variant = lifecycle.create_variant(pool, "co-001", "Examiner B")
    pool.find("co-001").path.unlink()
    codes = {f.code for f in check_pool(pool)}
    assert "variant_missing" in codes and "field_missing" in codes



def _draft_parent_with_variants(pool):
    """A draft practice question with two variants; the first sets its own level, the second inherits everything."""
    variants = [lifecycle.create_variant(pool, "co-001", "Examiner B") for _ in range(2)]
    editing.save(pool, variants[0].id, {"level": "remember"}, author="")
    return variants


def test_deleting_a_parent_needs_to_know_what_becomes_of_its_variants(pool):
    _draft_parent_with_variants(pool)
    with pytest.raises(lifecycle.LifecycleError) as caught:
        lifecycle.delete(pool, "co-001")
    assert caught.value.code == "has_variants"
    assert pool.find("co-001")  # nothing happened
    answer = Api().delete_question(str(pool.root), "co-001")
    assert answer["code"] == "has_variants" and answer["params"]["ids"] == "co-001-v1, co-001-v2, co-002"  # co-002: an imported variant


def test_deleting_a_parent_with_its_variants(pool):
    _draft_parent_with_variants(pool)
    result = lifecycle.delete(pool, "co-001", "delete")
    assert result["outcome"] == "deleted"
    assert [(v["id"], v["outcome"]) for v in result["variants"]] == [
        ("co-001-v1", "deleted"), ("co-001-v2", "deleted"), ("co-002", "deleted")]
    assert not pool.all_ids()


def test_detached_variants_become_questions_of_their_own(pool):
    parent_level = pool.find("co-001").level
    _draft_parent_with_variants(pool)
    result = lifecycle.delete(pool, "co-001", "detach")
    assert [(v["id"], v["new_id"]) for v in result["variants"]] == [
        ("co-001-v1", "co-003"), ("co-001-v2", "co-004"), ("co-002", "co-005")]
    assert pool.all_ids() == {"co-003", "co-004", "co-005"}
    own, inherited = pool.find("co-003"), pool.find("co-004")
    assert own.data["level"] == "remember"  # its own value stays
    assert inherited.data["level"] == parent_level and "type" in inherited.data  # inherited settings are written in
    assert not own.variant_of and not inherited.variant_of and not inherited.public and inherited.exam
    assert pool.next_id(pool.prefix_for("colours")) == "co-006"
    assert not [f for f in check_pool(pool) if f.question in ("co-003", "co-004") and f.severity == "error"]


def test_a_free_text_question_can_have_variants_that_inherit_lines_and_half_points(pool):
    task = pool.new_question("colours", "free_text", author="")
    task.data["stem"]["en"] = "A file of 3 MB is sent over a line of 8 Mbit/s. How long does it take?"
    task.data["half_points"] = True
    task.data["lines"] = 6
    task.save()
    variant = lifecycle.create_variant(pool, task.id, "Examiner B")
    assert variant.id == f"{task.id}-v1" and "lines" not in variant.data and "half_points" not in variant.data
    assert variant.data["stem"]["en"].startswith("A file of 3 MB")  # the text to vary, for example with other numbers
    loaded = pool.find(variant.id)
    assert loaded.type == "free_text" and loaded.get("lines") == 6 and loaded.get("half_points") is True
    editing.save(pool, variant.id, {"lines": 8}, author="")
    assert pool.find(variant.id).get("lines") == 8
    row = next(r for r in catalog.rows(pool) if r["id"] == task.id)
    assert row["variants"] == [variant.id]


def test_the_check_while_editing_a_variant_counts_empty_settings_as_inherited(pool):
    variant = lifecycle.create_variant(pool, "co-001", "Examiner B")
    fields = {"type": None, "level": None, "time_seconds": None, "coverage": "", "misconception": ""}
    codes = {f["code"] for f in editing.check_fields(pool, variant.id, fields)}
    assert "field_missing" not in codes
