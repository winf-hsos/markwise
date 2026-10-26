"""Help from a language model, tested without a network: the provider and the credential store are stand-ins."""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

from markwise import assist, settings
from markwise.app.api import Api
from markwise.pool import Pool, PoolSettings

LANGS = ["de", "en"]
QUESTION = {
    "type": "single", "created_by": "Examiner A", "coverage": "Deck 3",
    "stem": {"de": "Welche Farbe hat der Himmel?", "en": "What colour is the sky?"},
    "options": [
        {"id": "a", "correct": True, "text": {"de": "Blau", "en": "Blue"}, "feedback": {"de": "Ja.", "en": "Yes."}},
        {"id": "b", "correct": False, "text": {"de": "Grün", "en": "Green"}, "feedback": {"de": "Nein.", "en": "No."}},
    ],
}


@pytest.fixture
def provider(monkeypatch):
    """A stand-in for OpenAI and the credential store; records what would be sent."""
    sent = []
    store = {}
    answers = {}

    def request(method, path, key, body=None):
        sent.append({"method": method, "path": path, "key": key, "body": body})
        if not key.startswith("sk-good"):
            raise assist.AssistError("llm_key_invalid", "the API key was not accepted")
        if path == "/models":
            return {"data": [{"id": "gpt-test-mini"}, {"id": "gpt-test"}, {"id": "whisper-1"}, {"id": "text-embedding-3"}]}
        return {"choices": [{"message": {"content": json.dumps(answers[body["response_format"]["json_schema"]["name"]])}}]}

    monkeypatch.setattr(assist, "_request", request)
    monkeypatch.setattr(assist, "get_key", lambda: store.get("key", ""))
    monkeypatch.setattr(assist, "set_key", lambda key: store.__setitem__("key", key))
    monkeypatch.setattr(assist, "remove_key", lambda: store.pop("key", None))
    return {"sent": sent, "store": store, "answers": answers}


def switch_on(model="gpt-test-mini"):
    current = settings.load()
    current.update({"llm_enabled": True, "llm_model": model})
    settings.save(current)


def test_off_by_default_and_nothing_is_sent(provider):
    assert settings.load().llm_enabled is False
    with pytest.raises(assist.AssistError) as caught:
        assist.review(QUESTION, LANGS, "de", "de")
    assert caught.value.code == "llm_off" and provider["sent"] == []


def test_a_key_is_stored_only_after_the_provider_accepts_it(provider):
    api = Api()
    assert api.set_llm_key("sk-bad")["code"] == "llm_key_invalid" and "key" not in provider["store"]
    models = api.set_llm_key("sk-good")["data"]
    assert models == ["gpt-test-mini", "gpt-test"]  # no speech or embedding models
    assert provider["store"]["key"] == "sk-good" and api.llm_status()["data"]["has_key"] is True


def test_a_key_in_the_environment_is_offered_but_never_shown(provider, monkeypatch):
    api = Api()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert api.llm_status()["data"]["env_key"] == ""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-good-from-environment")
    status = api.llm_status()["data"]
    assert status["env_key"] == "sk-…ment" and "good" not in status["env_key"]
    assert api.use_env_llm_key()["data"] == ["gpt-test-mini", "gpt-test"]
    assert provider["store"]["key"] == "sk-good-from-environment"
    assert api.llm_status()["data"]["env_key"] == ""  # stored now, nothing left to offer
    monkeypatch.setenv("OPENAI_API_KEY", "sk-bad")
    provider["store"].clear()
    assert api.use_env_llm_key()["code"] == "llm_key_invalid" and "key" not in provider["store"]


def test_review_sends_only_the_question_in_every_language_and_proposes_real_changes(provider):
    provider["store"]["key"] = "sk-good"
    switch_on()
    provider["answers"]["question_review"] = {
        "findings": [{"about": "option.a.text", "text": "Die richtige Option ist deutlich kürzer."},
                     {"about": "question", "text": "Text und Optionen passen zusammen."}],
        "changes": [{"field": "option.a.text", "texts": {"de": "Blau, weil kurzwelliges Licht stärker gestreut wird",
                                                          "en": "Blue"}},  # en unchanged: dropped
                    {"field": "option.b.text", "texts": {"de": "Grün", "en": "Green"}},  # unchanged: dropped
                    {"field": "option.a.text", "texts": {"de": "noch einmal", "en": "again"}}],  # twice: first counts
    }
    answer = assist.review(QUESTION, LANGS, "de", "de", min_options=2)
    assert [f["about"] for f in answer["findings"]] == ["option.a.text", "question"]
    assert answer["changes"] == [{"field": "option.a.text", "lang": "de",
                                  "text": "Blau, weil kurzwelliges Licht stärker gestreut wird", "before": "Blau"}]
    assert answer["new_options"] == []
    body = provider["sent"][-1]["body"]
    schema = body["response_format"]["json_schema"]["schema"]
    assert "new_options" not in schema["properties"]  # enough options: nothing to add
    item = schema["properties"]["changes"]["items"]["properties"]
    assert item["field"]["enum"] == ["stem", "option.a.text", "option.a.feedback", "option.b.text", "option.b.feedback"]
    assert item["texts"]["required"] == LANGS
    sent_text = json.dumps(body["messages"], ensure_ascii=False)
    assert "[de] Welche Farbe hat der Himmel?" in sent_text and "[en] What colour is the sky?" in sent_text
    assert "Never change which options are correct" in sent_text and "wrong language" in sent_text
    assert "Examiner A" not in sent_text and "Deck 3" not in sent_text  # no names, no other fields
    assert body["model"] == "gpt-test-mini" and body["response_format"]["json_schema"]["strict"] is True


def test_review_fills_missing_languages_and_adds_the_wrong_options_that_are_missing(provider):
    provider["store"]["key"] = "sk-good"
    switch_on()
    question = {"type": "single", "stem": {"de": "Welche Farbe hat der Himmel?", "en": ""},
                "options": [{"id": "a", "correct": True, "text": {"de": "Blau", "en": ""}, "feedback": {"de": "", "en": ""}},
                            {"id": "b", "correct": False, "text": {"de": "Grün", "en": ""}, "feedback": {"de": "", "en": ""}}]}
    texts = lambda de, en: {"de": de, "en": en}  # noqa: E731
    provider["answers"]["question_review"] = {
        "findings": [],
        "changes": [{"field": "stem", "texts": texts("Welche Farbe hat der Himmel?", "What colour is the sky?")},
                    {"field": "option.a.feedback", "texts": texts("Ja, Streuung.", "Yes, scattering.")}],
        "new_options": [{"text": texts("Rot", "Red"), "feedback": texts("Nein.", "No."), "misconception": "Abendrot"},
                        {"text": texts("Weiß", "White"), "feedback": texts("Nein.", "No."), "misconception": "Wolken"},
                        {"text": texts("Gelb", "Yellow"), "feedback": texts("Nein.", "No."), "misconception": "Sonne"}],
    }
    answer = assist.review(question, LANGS, "de", "de", min_options=4)
    assert [(c["field"], c["lang"], c["before"]) for c in answer["changes"]] == [
        ("stem", "en", ""), ("option.a.feedback", "de", ""), ("option.a.feedback", "en", "")]
    assert [o["text"]["en"] for o in answer["new_options"]] == ["Red", "White"]  # two missing, no more
    body = provider["sent"][-1]["body"]
    assert "propose exactly 2 new wrong options" in json.dumps(body["messages"])
    new = body["response_format"]["json_schema"]["schema"]["properties"]["new_options"]["items"]["properties"]
    assert new["text"]["required"] == LANGS


def test_review_of_a_free_text_question_covers_the_expected_answer(provider):
    provider["store"]["key"] = "sk-good"
    switch_on()
    provider["answers"]["question_review"] = {"findings": [], "changes": [{"field": "expected", "texts": {"de": "Zwei: 0 und 1"}}]}
    question = {"type": "free_text", "created_by": "Examiner A", "stem": {"de": "Wie viele Ziffern hat das Binärsystem?"},
                "expected": {"de": "Zwei"}, "marking_notes": {"de": ""}}
    answer = assist.review(question, ["de"], "de", "de")
    assert answer["changes"] == [{"field": "expected", "lang": "de", "text": "Zwei: 0 und 1", "before": "Zwei"}]
    body = provider["sent"][-1]["body"]
    schema = body["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["changes"]["items"]["properties"]["field"]["enum"] == ["stem", "expected", "marking_notes"]
    assert "new_options" not in schema["properties"]
    sent_text = json.dumps(body["messages"], ensure_ascii=False)
    assert "Expected answer:\\n  [de] Zwei" in sent_text and "Examiner A" not in sent_text


def test_the_api_names_what_is_missing(provider, tmp_path):
    pool = str(Pool.create(tmp_path / "pool", PoolSettings(name="P")).root)
    api = Api()
    assert api.assist_review(pool, QUESTION, "de")["code"] == "llm_off"
    current = settings.load()
    current.update({"llm_enabled": True})
    settings.save(current)
    assert api.assist_review(pool, QUESTION, "de")["code"] == "llm_no_key"
    provider["store"]["key"] = "sk-good"
    assert api.assist_vary_numbers(pool, {"type": "free_text", "stem": {"de": "1 + 1?"}})["code"] == "llm_no_model"


def test_http_errors_become_readable_codes(monkeypatch):
    def fail(status, message):
        def urlopen(request, timeout):
            raise urllib.error.HTTPError(request.full_url, status, "error", {}, io.BytesIO(json.dumps({"error": {"message": message}}).encode()))
        return urlopen
    monkeypatch.setattr(assist.urllib.request, "urlopen", fail(401, "bad key"))
    with pytest.raises(assist.AssistError) as caught:
        assist.list_models("sk-x")
    assert caught.value.code == "llm_key_invalid"
    monkeypatch.setattr(assist.urllib.request, "urlopen", fail(429, "You exceeded your quota"))
    with pytest.raises(assist.AssistError) as caught:
        assist.list_models("sk-x")
    assert caught.value.code == "llm_quota" and "quota" in str(caught.value)


def test_new_numbers_come_with_the_worked_out_answer_in_every_language(provider):
    provider["store"]["key"] = "sk-good"
    switch_on()
    task = {"type": "free_text", "created_by": "Examiner A",
            "stem": {"de": "3 MB werden mit 8 Mbit/s gesendet. Wie lange dauert das?", "en": "3 MB are sent at 8 Mbit/s. How long?"},
            "expected": {"de": "3 s", "en": "3 s"}, "marking_notes": {"de": "", "en": ""}}
    provider["answers"]["number_variant"] = {
        "calculation": "5 MB = 40 Mbit; 40 Mbit / 10 Mbit/s = 4 s",
        "findings": [],
        "changes": [{"field": "stem", "texts": {"de": "5 MB werden mit 10 Mbit/s gesendet. Wie lange dauert das?",
                                                 "en": "5 MB are sent at 10 Mbit/s. How long?"}},
                    {"field": "expected", "texts": {"de": "4 s", "en": "4 s"}},
                    {"field": "marking_notes", "texts": {"de": "", "en": ""}}]}  # empty in the original: nothing
    answer = assist.vary_numbers(task, LANGS, "de")
    assert answer["calculation"].endswith("= 4 s")
    assert [(c["field"], c["lang"]) for c in answer["changes"]] == [("stem", "de"), ("stem", "en"), ("expected", "de"), ("expected", "en")]
    sent_text = json.dumps(provider["sent"][-1]["body"]["messages"], ensure_ascii=False)
    assert "[de] 3 MB werden" in sent_text and "Examiner A" not in sent_text
    with pytest.raises(assist.AssistError) as caught:
        assist.vary_numbers(QUESTION, LANGS, "de")
    assert caught.value.code == "llm_not_free_text"


def test_the_command_line_shows_the_model_a_variant_with_its_inherited_settings(provider, tmp_path):
    from markwise import lifecycle
    from markwise.cli import _model_fields
    pool = Pool.create(tmp_path / "pool", PoolSettings(name="P", languages=["de"]))
    task = pool.new_question("transfer", "free_text", author="")
    variant = lifecycle.create_variant(pool, task.id, "")
    fields = _model_fields(pool, variant.id)
    assert "type" not in variant.data and fields["type"] == "free_text" and fields["lines"] == 8


def _pool_with_figures(tmp_path):
    import pymupdf
    pool = Pool.create(tmp_path / "pool", PoolSettings(name="P", languages=["de"]))
    (pool.images_dir / "curve.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100"><path d="M0 100 L200 0" stroke="black"/></svg>',
        encoding="utf-8")
    pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 3000, 1500), 0).save(str(pool.images_dir / "photo.png"))
    return pool


def test_figures_go_to_the_model_as_png_images_after_the_text(provider, tmp_path):
    import base64
    import pymupdf
    pool = _pool_with_figures(tmp_path)
    provider["store"]["key"] = "sk-good"
    switch_on()
    provider["answers"]["question_review"] = {"findings": [], "changes": []}
    fields = {**QUESTION, "images": ["curve", "photo", "missing"]}
    figures = assist.figures_for_model(pool, fields)
    assert len(figures) == 2 and all(url.startswith("data:image/png;base64,") for url in figures)  # the missing one is left out
    photo = pymupdf.Pixmap(base64.b64decode(figures[1].split(",", 1)[1]))
    assert max(photo.width, photo.height) <= assist.FIGURE_MAX_PIXELS  # scaled down
    Api().assist_review(str(pool.root), fields, "de")
    content = provider["sent"][-1]["body"]["messages"][1]["content"]
    assert content[0]["type"] == "text" and "Figures below the text: curve, photo, missing" in content[0]["text"]
    assert [part["type"] for part in content[1:]] == ["image_url", "image_url"]
    assert "figures that belong to the question are attached" in provider["sent"][-1]["body"]["messages"][0]["content"]


def test_without_figures_the_question_goes_as_plain_text(provider):
    provider["store"]["key"] = "sk-good"
    switch_on()
    provider["answers"]["question_review"] = {"findings": [], "changes": []}
    assist.review(QUESTION, LANGS, "de", "de", min_options=2)
    assert isinstance(provider["sent"][-1]["body"]["messages"][1]["content"], str)


def test_a_model_without_eyes_gets_a_clear_message(monkeypatch):
    def urlopen(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 400, "error", {}, io.BytesIO(
            json.dumps({"error": {"message": "Invalid content type. image_url is only supported by certain models."}}).encode()))
    monkeypatch.setattr(assist.urllib.request, "urlopen", urlopen)
    with pytest.raises(assist.AssistError) as caught:
        assist._request("POST", "/chat/completions", "sk-x", {})
    assert caught.value.code == "llm_no_vision"


def test_the_level_is_judged_and_a_different_one_proposed(provider):
    provider["store"]["key"] = "sk-good"
    switch_on()
    question = {**QUESTION, "level": "apply"}
    provider["answers"]["question_review"] = {
        "findings": [{"about": "level", "text": "Die Frage fragt nur eine Tatsache ab."}], "changes": [], "level": "remember"}
    answer = assist.review(question, LANGS, "de", "de", min_options=2)
    assert answer["level"] == {"before": "apply", "proposed": "remember"}
    assert answer["findings"] == [{"about": "level", "text": "Die Frage fragt nur eine Tatsache ab."}]
    body = provider["sent"][-1]["body"]
    assert "Level: apply" in body["messages"][1]["content"] and "cognitive level" in body["messages"][0]["content"]
    schema = body["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["level"]["enum"] == ["remember", "understand", "apply"] and "level" in schema["required"]

    provider["answers"]["question_review"] = {"findings": [], "changes": [], "level": "apply"}
    assert assist.review(question, LANGS, "de", "de", min_options=2)["level"] is None  # fits: nothing to propose
