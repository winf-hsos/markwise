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
        assist.check_stem(QUESTION, LANGS, "de", "de")
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


def test_check_stem_sends_only_the_question_and_returns_the_suggestion_in_every_language(provider):
    provider["store"]["key"] = "sk-good"
    switch_on()
    provider["answers"]["stem_review"] = {"findings": ["Zu kurz."], "suggestion": {
        "de": "Welche Farbe hat ein klarer Taghimmel?", "en": "What colour is a clear daytime sky?"}}
    answer = assist.check_stem(QUESTION, LANGS, "de", "de")
    assert answer["suggestion"] == {"de": "Welche Farbe hat ein klarer Taghimmel?", "en": "What colour is a clear daytime sky?"}
    body = provider["sent"][-1]["body"]
    sent_text = json.dumps(body["messages"], ensure_ascii=False)
    assert body["model"] == "gpt-test-mini" and "[de] Welche Farbe hat der Himmel?" in sent_text
    assert "[en] What colour is the sky?" in sent_text  # every language, labelled, so that a wrong one shows
    assert "Examiner A" not in sent_text and "Deck 3" not in sent_text  # no names, no other fields
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["response_format"]["json_schema"]["schema"]["properties"]["suggestion"]["required"] == LANGS


def test_a_text_in_the_wrong_language_is_shown_to_the_model_with_its_label(provider):
    provider["store"]["key"] = "sk-good"
    switch_on()
    provider["answers"]["stem_review"] = {"findings": ["Der englische Text ist auf Deutsch."], "suggestion": {"en": "How many?"}}
    question = {"type": "free_text", "created_by": "Examiner A", "stem": {"en": "Wie viele Symbole hat das Binärsystem?"},
                "expected": {"en": "Zwei"}, "marking_notes": {"en": ""}}
    answer = assist.check_stem(question, ["en"], "en", "de")
    assert answer["findings"] == ["Der englische Text ist auf Deutsch."]
    sent_text = json.dumps(provider["sent"][-1]["body"]["messages"], ensure_ascii=False)
    assert "[en] Wie viele Symbole" in sent_text and "[en] Zwei" in sent_text and "wrong language" in sent_text
    assert "Examiner A" not in sent_text


def test_review_of_the_whole_question_proposes_only_real_changes_per_language(provider):
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
    answer = assist.review_question(QUESTION, LANGS, "de", "de")
    assert [f["about"] for f in answer["findings"]] == ["option.a.text", "question"]
    assert answer["changes"] == [{"field": "option.a.text", "lang": "de",
                                  "text": "Blau, weil kurzwelliges Licht stärker gestreut wird", "before": "Blau"}]
    schema = provider["sent"][-1]["body"]["response_format"]["json_schema"]["schema"]
    item = schema["properties"]["changes"]["items"]["properties"]
    assert item["field"]["enum"] == ["stem", "option.a.text", "option.a.feedback", "option.b.text", "option.b.feedback"]
    assert item["texts"]["required"] == LANGS
    sent_text = json.dumps(provider["sent"][-1]["body"]["messages"], ensure_ascii=False)
    assert "Never change which options are correct" in sent_text and "Examiner A" not in sent_text


def test_review_of_a_free_text_question_covers_the_expected_answer(provider):
    provider["store"]["key"] = "sk-good"
    switch_on()
    provider["answers"]["question_review"] = {"findings": [], "changes": [{"field": "expected", "texts": {"de": "Zwei: 0 und 1"}}]}
    question = {"type": "free_text", "stem": {"de": "Wie viele Ziffern hat das Binärsystem?"}, "expected": {"de": "Zwei"}}
    assert assist.review_question(question, ["de"], "de", "de")["changes"] == [
        {"field": "expected", "lang": "de", "text": "Zwei: 0 und 1", "before": "Zwei"}]
    schema = provider["sent"][-1]["body"]["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["changes"]["items"]["properties"]["field"]["enum"] == ["stem", "expected", "marking_notes"]


def test_translation_fills_the_other_languages_and_keeps_what_is_right(provider):
    provider["store"]["key"] = "sk-good"
    switch_on()
    question = {"type": "single", "stem": {"de": "Welche Farbe hat der Himmel?", "en": ""},
                "options": [{"id": "a", "correct": True, "text": {"de": "Blau", "en": "Blue"}, "feedback": {"de": "Ja.", "en": ""}},
                            {"id": "b", "correct": False, "text": {"de": "Grün", "en": ""}, "feedback": {"de": "", "en": ""}}]}
    provider["answers"]["translation"] = {"findings": [], "translations": [
        {"field": "stem", "texts": {"en": "What colour is the sky?"}},
        {"field": "option.a.text", "texts": {"en": "Blue"}},  # already right: dropped
        {"field": "option.a.feedback", "texts": {"en": "Yes."}},
        {"field": "option.b.text", "texts": {"en": "Green"}}]}
    answer = assist.translate(question, LANGS, "de", "de")
    assert [(c["field"], c["lang"], c["text"]) for c in answer["changes"]] == [
        ("stem", "en", "What colour is the sky?"), ("option.a.feedback", "en", "Yes."), ("option.b.text", "en", "Green")]
    schema = provider["sent"][-1]["body"]["response_format"]["json_schema"]["schema"]
    item = schema["properties"]["translations"]["items"]["properties"]
    assert item["texts"]["required"] == ["en"]  # only the target languages
    assert "option.b.feedback" not in item["field"]["enum"]  # nothing to translate where the source is empty
    with pytest.raises(assist.AssistError) as caught:
        assist.translate(question, ["de"], "de", "de")
    assert caught.value.code == "llm_one_language"


def test_distractors_come_in_every_language_and_no_more_than_asked(provider):
    provider["store"]["key"] = "sk-good"
    switch_on()
    texts = lambda de, en: {"de": de, "en": en}  # noqa: E731
    provider["answers"]["distractors"] = {"distractors": [
        {"text": texts("Rot", "Red"), "feedback": texts("Nein.", "No."), "misconception": "Abendrot"},
        {"text": texts("Weiß", "White"), "feedback": texts("Nein.", "No."), "misconception": "Wolken"},
        {"text": texts("Gelb", "Yellow"), "feedback": texts("Nein.", "No."), "misconception": "Sonne"},
    ]}
    proposals = assist.distractors(QUESTION, LANGS, 2, "de")
    assert [p["text"]["en"] for p in proposals] == ["Red", "White"]
    schema = provider["sent"][-1]["body"]["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["distractors"]["items"]["properties"]["text"]["required"] == ["de", "en"]


def test_the_api_names_what_is_missing(provider, tmp_path):
    pool = str(Pool.create(tmp_path / "pool", PoolSettings(name="P")).root)
    api = Api()
    assert api.assist_check_stem(pool, QUESTION, "de")["code"] == "llm_off"
    current = settings.load()
    current.update({"llm_enabled": True})
    settings.save(current)
    assert api.assist_check_stem(pool, QUESTION, "de")["code"] == "llm_no_key"
    provider["store"]["key"] = "sk-good"
    assert api.assist_translate(pool, QUESTION, "de")["code"] == "llm_no_model"


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
