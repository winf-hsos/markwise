"""Editing questions without disturbing the rest of their files, with invented questions only."""

from __future__ import annotations

import os

import pytest

from markwise import editing
from markwise.app.api import Api
from markwise.catalog import plain
from markwise.importer import import_pool
from markwise.pool import Pool
from markwise.question import ConflictError

from test_core import write_legacy


@pytest.fixture
def pool(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKWISE_HOME", str(tmp_path / "home"))
    import_pool(write_legacy(tmp_path / "legacy"), tmp_path / "pool")
    return Pool.open(tmp_path / "pool")


def fields_of(pool: Pool, qid: str) -> dict:
    data = pool.find(qid).data
    return {k: plain(data[k]) for k in editing.EDITABLE if k in data}


def test_saving_without_changes_keeps_the_file(pool):
    path = pool.find("co-001").path
    before = path.read_bytes()
    _, changed = editing.save(pool, "co-001", fields_of(pool, "co-001"))
    assert not changed and path.read_bytes() == before


def test_a_change_touches_only_its_own_line(pool):
    path = pool.find("co-001").path
    before = path.read_text(encoding="utf-8").splitlines()
    fields = fields_of(pool, "co-001")
    fields["options"][1]["text"]["de"] = "Dunkelgrün"
    editing.save(pool, "co-001", fields, author="")  # without an author, so that only the text line changes
    after = path.read_text(encoding="utf-8").splitlines()
    changed = [(b, a) for b, a in zip(before, after) if b != a]
    assert len(before) == len(after) and len(changed) == 1
    assert 'de: "Dunkelgrün"' in changed[0][1]  # the quotes of the original stay
    assert "# a field the schema does not know" in path.read_text(encoding="utf-8")


def test_options_are_matched_by_id(pool):
    fields = fields_of(pool, "co-001")
    fields["options"] = [o for o in fields["options"] if o["id"] != "c"]
    fields["options"].append({"id": "e", "correct": False, "text": {"de": "Lila", "en": "Purple"},
                              "feedback": {"de": "Nein.", "en": "No."}})
    editing.save(pool, "co-001", fields)
    q = pool.find("co-001")
    assert [o["id"] for o in q.options] == ["a", "b", "d", "e"] and q.options[3]["text"]["en"] == "Purple"


def test_emptied_optional_fields_disappear_and_new_ones_find_their_place(pool):
    fields = fields_of(pool, "co-001")
    fields["coverage"] = ""
    fields["code"] = "print('sky')"
    editing.save(pool, "co-001", fields)
    q = pool.find("co-001")
    keys = list(q.data.keys())
    assert "coverage" not in keys and keys.index("code") == keys.index("image") + 1  # stem, image, code


def test_a_released_question_stays_released_when_its_content_changes(pool):
    q = pool.find("co-001")
    q.data["status"] = "released"
    q.data["released_by"] = ["Examiner A", "Examiner B"]
    q.save()
    fields = fields_of(pool, "co-001")
    fields["stem"]["en"] = "Which colour has the sky on a clear day?"
    question, changed = editing.save(pool, "co-001", fields)
    assert changed and question.status == "released" and list(question.data["released_by"]) == ["Examiner A", "Examiner B"]


def test_files_from_before_releases_had_their_name_are_read_and_written_anew(pool):
    path = pool.find("co-001").path
    text = path.read_text(encoding="utf-8")
    assert "status: draft\n" in text
    path.write_text(text.replace("status: draft\n", "status: reviewed\nreviewed_by:\n  - Examiner A\n"), encoding="utf-8")
    question = Pool.open(pool.root).find("co-001")
    assert question.status == "released" and list(question.data["released_by"]) == ["Examiner A"]
    fields = fields_of(pool, "co-001")
    fields["stem"]["en"] = "Which colour has the sky on a clear day?"
    editing.save(Pool.open(pool.root), "co-001", fields)
    saved = path.read_text(encoding="utf-8")
    assert "status: released\nreleased_by:\n  - Examiner A\n" in saved and "reviewed" not in saved


def test_a_change_elsewhere_is_not_overwritten(pool):
    q = pool.find("co-001")
    opened = q.path.stat().st_mtime_ns
    os.utime(q.path, ns=(opened + 10_000_000, opened + 10_000_000))  # someone saved in between
    fields = fields_of(pool, "co-001")
    fields["level"] = "apply"
    with pytest.raises(ConflictError):
        editing.save(pool, "co-001", fields, expected_mtime_ns=opened)
    editing.save(pool, "co-001", fields, expected_mtime_ns=opened, force=True)
    assert pool.find("co-001").level == "apply"


def test_check_fields_sees_unsaved_changes(pool):
    fields = fields_of(pool, "co-001")
    fields["options"][1]["correct"] = True
    messages = [f["message"] for f in editing.check_fields(pool, "co-001", fields)]
    assert any("exactly one correct option" in m for m in messages)
    assert pool.find("co-001").correct_ids == ["a"]  # nothing was saved


@pytest.mark.parametrize("path, value, check", [
    ("level", "apply", lambda q: q.level == "apply"),
    ("stem.en", "Sky colour?", lambda q: q.data["stem"]["en"] == "Sky colour?"),
    ("options.b.correct", "true", lambda q: q.correct_ids == ["a", "b"]),
    ("public", "false", lambda q: q.public is False),
])
def test_set_field_by_dotted_path(pool, path, value, check):
    editing.set_field(pool, "co-001", path, value)
    assert check(pool.find("co-001"))


def test_set_field_refuses_fields_that_belong_elsewhere(pool):
    with pytest.raises(ValueError):
        editing.set_field(pool, "co-001", "status", "released")


def test_api_creates_questions_in_existing_or_named_new_concepts(pool):
    api = Api()
    assert api.create_question(str(pool.root), "planets", "single")["code"] == "concept_unknown"
    created = api.create_question(str(pool.root), "shapes", "multiple")["data"]
    assert created["id"] == "s-001" and created["data"]["type"] == "multiple" and created["concept_name"] == "Shapes"
    new = api.create_question(str(pool.root), "", "single", {"name": "Größen und Maße", "description": "Wie viel wovon."})["data"]
    assert new["data"]["concept"] == "groessen-und-masse" and new["concept_name"] == "Größen und Maße"
    assert api.create_question(str(pool.root), "", "single", {"name": "größen und maße"})["code"] == "concept_exists"
    assert api.create_question(str(pool.root), "", "single", {"name": " "})["code"] == "concept_name_missing"


def test_concepts_are_renamed_without_moving(pool):
    api = Api()
    renamed = api.update_concept(str(pool.root), "colours", "Farben", "Was wir sehen.")["data"]
    assert renamed == {"id": "colours", "name": "Farben", "description": "Was wir sehen.", "named": True}
    assert (pool.root / "questions" / "colours").is_dir()
    listed = {c["id"]: c for c in api.list_concepts(str(pool.root))["data"]}
    assert listed["colours"]["questions"] == 2 and listed["shapes"]["questions"] == 0


def test_slugs_and_folder_pools(tmp_path):
    from markwise.pool import PoolSettings, slugify
    assert slugify("Zahlensysteme & Codes!") == "zahlensysteme-codes" and slugify("ÄÖÜ ß") == "aeoeue-ss"
    folder_pool = Pool.create(tmp_path / "p", PoolSettings(name="P"))
    (folder_pool.questions_dir / "old-topic").mkdir()
    assert folder_pool.concept_info()[0]["name"] == "Old topic"  # stand-in until it is named
    cid = folder_pool.add_concept("Old topic")  # same name as the stand-in, but no real name yet
    assert cid == "old-topic-2" and set(Pool.open(folder_pool.root).concepts()) == {"old-topic", "old-topic-2"}


def test_api_save_reports_a_conflict(pool):
    api = Api()
    detail = api.get_question(str(pool.root), "co-001")["data"]
    path = pool.find("co-001").path
    assert isinstance(detail["mtime_ns"], str)  # nanoseconds do not survive a JavaScript number
    assert api.save_question(str(pool.root), "co-001", fields_of(pool, "co-001"), detail["mtime_ns"])["data"]["changed"] is False
    os.utime(path, ns=(int(detail["mtime_ns"]) + 10_000_000,) * 2)
    fields = fields_of(pool, "co-001")
    fields["level"] = "remember"
    assert api.save_question(str(pool.root), "co-001", fields, detail["mtime_ns"])["code"] == "conflict"


# --- practice and exam at once ---------------------------------------------------------


def test_exam_defaults_to_not_public(pool):
    assert pool.find("co-001").exam is False and pool.find("co-002").exam is True


def test_exam_is_written_only_where_it_differs_from_its_default(pool):
    path = pool.find("co-001").path
    fields = fields_of(pool, "co-001")
    fields["exam"] = True  # practice and exam
    editing.save(pool, "co-001", fields)
    q = pool.find("co-001")
    assert q.public and q.exam and list(q.data.keys()).index("exam") == list(q.data.keys()).index("public") + 1
    fields["exam"] = False  # back to practice only: the field goes again
    editing.save(pool, "co-001", fields)
    assert "exam" not in pool.find("co-001").data and "exam:" not in path.read_text(encoding="utf-8")


def test_checks_for_the_use_of_a_question(pool):
    from markwise.checks import check_pool
    q = pool.find("co-001")
    q.data["exam"] = True
    q.save()
    codes = {f.code for f in check_pool(pool) if f.question == "co-001"}
    assert "no_variant" not in codes  # a question for both needs no exam variant
    q = pool.find("co-001")
    q.data["public"] = False
    q.data["exam"] = False
    q.save()
    assert "no_use" in {f.code for f in check_pool(pool) if f.question == "co-001"}


def test_rows_carry_exam_and_modified(pool):
    from markwise.catalog import rows
    row = next(r for r in rows(pool) if r["id"] == "co-002")
    assert row["exam"] is True and row["public"] is False and row["modified"] > 0


def test_code_language_is_optional(pool):
    fields = fields_of(pool, "co-001")
    fields["code"] = "print('sky')"
    fields["code_language"] = "python"
    editing.save(pool, "co-001", fields)
    assert pool.find("co-001").get("code_language") == "python"
    fields["code"] = ""
    fields["code_language"] = ""
    editing.save(pool, "co-001", fields)
    assert "code" not in pool.find("co-001").data and "code_language" not in pool.find("co-001").data


# --- figures --------------------------------------------------------------------------


def test_images_are_listed_with_previews_and_added_under_a_clean_name(pool, tmp_path):
    api = Api()
    listed = api.list_images(str(pool.root))["data"]
    assert [i["name"] for i in listed] == ["sky"] and listed[0]["data"].startswith("data:image/svg+xml;base64,")
    source = tmp_path / "Mein Bild Ä.svg"
    source.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    added = api.add_image(str(pool.root), str(source))["data"]
    assert added["name"] == "mein-bild-ae" and (pool.images_dir / "mein-bild-ae.svg").exists()
    assert api.add_image(str(pool.root), str(source))["data"]["name"] == "mein-bild-ae"  # the same picture again
    other = tmp_path / "mein bild ä.png"
    other.write_bytes(b"\x89PNG not really")
    assert api.add_image(str(pool.root), str(other))["data"]["name"] == "mein-bild-ae-2"


def test_add_image_refuses_other_files(pool, tmp_path):
    text = tmp_path / "notes.txt"
    text.write_text("no picture", encoding="utf-8")
    assert Api().add_image(str(pool.root), str(text))["code"] == "image_type"
    assert Api().add_image(str(pool.root), str(tmp_path / "missing.png"))["code"] == "image_missing"


def test_a_jpeg_figure_passes_the_check(pool):
    from markwise.checks import check_pool
    (pool.images_dir / "photo.jpg").write_bytes(b"\xff\xd8 not really")
    q = pool.find("co-001")
    q.data["image"] = "photo"
    q.save()
    assert "image_missing" not in {f.code for f in check_pool(pool) if f.question == "co-001"}


def test_several_figures_are_stored_with_their_layout_and_one_stays_short(pool):
    (pool.images_dir / "sun.svg").write_text("<svg/>", encoding="utf-8")
    path = pool.find("co-001").path
    fields = fields_of(pool, "co-001")
    fields["images"] = ["sky", "sun"]
    fields["image_columns"] = 2
    editing.save(pool, "co-001", fields)
    q = pool.find("co-001")
    assert q.images == ["sky", "sun"] and q.image_columns == 2 and "image" not in q.data
    assert list(q.data.keys()).index("images") == list(q.data.keys()).index("stem") + 1
    fields = fields_of(pool, "co-001")
    fields["images"] = ["sun"]
    fields["image_columns"] = 2
    editing.save(pool, "co-001", fields)
    q = pool.find("co-001")
    assert q.data["image"] == "sun" and "images" not in q.data and "image_columns" not in q.data
    assert "image_columns" not in path.read_text(encoding="utf-8")


def test_saving_a_question_with_one_figure_untouched_keeps_the_file(pool):
    path = pool.find("co-001").path
    before = path.read_bytes()
    fields = fields_of(pool, "co-001")
    fields["images"] = ["sky"]  # how the window sends the one figure back
    fields["image_columns"] = 1
    _, changed = editing.save(pool, "co-001", fields)
    assert not changed and path.read_bytes() == before


def test_missing_figures_and_bad_layouts_are_found(pool):
    from markwise.checks import check_pool
    q = pool.find("co-001")
    q.data["images"] = ["sky", "moon"]
    q.data["image_columns"] = 7
    q.save()
    codes = [f.code for f in check_pool(pool) if f.question == "co-001"]
    assert "image_missing" in codes and "image_columns" in codes


# --- the concepts page ------------------------------------------------------------------


def test_concept_overview_summarises_the_questions(pool, tmp_path):
    from markwise.module import Module
    module = Module.create(tmp_path / "module", "M", "M", pools=[pool.root])
    overview = {c["id"]: c for c in Api().concept_overview(str(module.root))["data"]}
    colours = overview["colours"]
    assert colours["name"] == "Colours of Things" and colours["questions"] == 2
    assert colours["levels"]["understand"] == 2 and colours["types"] == {"single": 1, "multiple": 1, "free_text": 0}
    assert (colours["practice"], colours["exam"], colours["without_variant"]) == (1, 1, 0)
    assert overview["shapes"]["questions"] == 0


def test_only_empty_concepts_can_be_deleted(pool):
    api = Api()
    assert api.delete_concept(str(pool.root), "colours")["code"] == "concept_not_empty"
    api.delete_concept(str(pool.root), "shapes")
    assert "shapes" not in Pool.open(pool.root).concepts()
    assert "colours" in Pool.open(pool.root).concepts()



# --- time and authorship ----------------------------------------------------------------


def test_new_questions_record_their_author_and_time(pool):
    from markwise import settings
    s = settings.load()
    s.update({"examiner": "Examiner A"})
    settings.save(s)
    q = pool.new_question("colours", "single")
    assert q.get("created_by") == "Examiner A" and len(str(q.get("created_at"))) == 10 and q.get("time_seconds") == 60
    assert "created_at: 20" in q.path.read_text(encoding="utf-8")  # a plain date, not a quoted string


def test_saving_records_who_changed_a_question(pool):
    fields = fields_of(pool, "co-001")
    fields["time_seconds"] = 45
    editing.save(pool, "co-001", fields, author="Examiner B")
    q = pool.find("co-001")
    assert q.get("time_seconds") == 45 and q.get("changed_by") == "Examiner B" and q.get("changed_at")
    keys = list(q.data.keys())
    assert keys.index("time_seconds") == keys.index("level") + 1
    _, changed = editing.save(pool, "co-001", fields_of(pool, "co-001"), author="Examiner C")
    assert not changed and pool.find("co-001").get("changed_by") == "Examiner B"  # nothing changed, nobody recorded


def test_without_a_name_the_windows_user_is_the_author(pool, monkeypatch):
    from markwise.question import default_author
    monkeypatch.setenv("USERNAME", "winuser")
    assert default_author() == "winuser"


@pytest.mark.parametrize("value, code", [(None, "no_time"), (2, "time_invalid"), ("1 min", "time_invalid"), (90, None)])
def test_time_is_checked(pool, value, code):
    from markwise.checks import check_pool
    q = pool.find("co-001")
    if value is None:
        q.data.pop("time_seconds", None)
    else:
        q.data["time_seconds"] = value
    q.save()
    codes = {f.code for f in check_pool(pool) if f.question == "co-001"}
    assert (code in codes) if code else not ({"no_time", "time_invalid"} & codes)


def test_an_unset_time_leaves_the_file_alone(pool):
    path = pool.find("co-002").path
    before = path.read_bytes()
    fields = fields_of(pool, "co-002")
    fields["time_seconds"] = None  # how the window sends a question without a time
    _, changed = editing.save(pool, "co-002", fields, author="")
    assert not changed and path.read_bytes() == before
