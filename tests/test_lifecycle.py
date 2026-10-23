"""Release, exam variants, retiring and taking back, with invented questions only."""

from __future__ import annotations

import pytest

from markwise import lifecycle
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
    assert variant.id == "co-003" and variant.variant_of == "co-001" and not variant.public and variant.exam
    assert variant.status == "draft" and "reviewed_by" not in variant.data and variant.get("created_by") == "Examiner B"
    assert variant.data["stem"]["en"] == pool.find("co-001").data["stem"]["en"]
    assert variant.path == pool.path_for("colours", "co-003")
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
    assert json.loads(capsys.readouterr().out)["id"] == "co-003"
    assert main(["question", "retire", str(pool.root), "co-003"]) == 0
    assert pool.find("co-003").status == "retired"
