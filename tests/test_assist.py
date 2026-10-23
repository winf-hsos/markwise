"""Help from a language model, tested without a network: the provider and the credential store are stand-ins."""

from __future__ import annotations

import io
import json
import urllib.error

import pytest

from markwise import assist, settings
from markwise.app.api import Api

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
        assist.check_stem(QUESTION, "de", "de")
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


def test_check_stem_sends_only_the_question_and_returns_the_suggestion(provider):
    provider["store"]["key"] = "sk-good"
    switch_on()
    provider["answers"]["stem_review"] = {"findings": ["Zu kurz."], "suggestion": "Welche Farbe hat ein klarer Taghimmel?"}
    answer = assist.check_stem(QUESTION, "de", "de")
    assert answer["suggestion"].startswith("Welche Farbe")
    body = provider["sent"][-1]["body"]
    sent_text = json.dumps(body["messages"], ensure_ascii=False)
    assert body["model"] == "gpt-test-mini" and "Welche Farbe hat der Himmel?" in sent_text
    assert "Examiner A" not in sent_text and "Deck 3" not in sent_text  # no names, no other fields
    assert body["response_format"]["json_schema"]["strict"] is True


def test_a_free_text_question_can_be_checked_with_its_expected_answer(provider):
    provider["store"]["key"] = "sk-good"
    switch_on()
    provider["answers"]["stem_review"] = {"findings": [], "suggestion": ""}
    question = {"type": "free_text", "created_by": "Examiner A", "stem": {"en": "How many symbols does the binary system have?"},
                "expected": {"en": "Two"}, "marking_notes": {"en": ""}}
    assert assist.check_stem(question, "en", "de") == {"findings": [], "suggestion": ""}
    sent_text = json.dumps(provider["sent"][-1]["body"]["messages"], ensure_ascii=False)
    assert "Expected answer:\\nTwo" in sent_text  # newline as encoded in JSON and "Examiner A" not in sent_text


def test_distractors_come_in_every_language_and_no_more_than_asked(provider):
    provider["store"]["key"] = "sk-good"
    switch_on()
    texts = lambda de, en: {"de": de, "en": en}  # noqa: E731
    provider["answers"]["distractors"] = {"distractors": [
        {"text": texts("Rot", "Red"), "feedback": texts("Nein.", "No."), "misconception": "Abendrot"},
        {"text": texts("Weiß", "White"), "feedback": texts("Nein.", "No."), "misconception": "Wolken"},
        {"text": texts("Gelb", "Yellow"), "feedback": texts("Nein.", "No."), "misconception": "Sonne"},
    ]}
    proposals = assist.distractors(QUESTION, ["de", "en"], 2, "de")
    assert [p["text"]["en"] for p in proposals] == ["Red", "White"]
    schema = provider["sent"][-1]["body"]["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["distractors"]["items"]["properties"]["text"]["required"] == ["de", "en"]


def test_the_api_names_what_is_missing(provider):
    api = Api()
    assert api.assist_check_stem(QUESTION, "de")["code"] == "llm_off"
    current = settings.load()
    current.update({"llm_enabled": True})
    settings.save(current)
    assert api.assist_check_stem(QUESTION, "de")["code"] == "llm_no_key"
    provider["store"]["key"] = "sk-good"
    assert api.assist_check_stem(QUESTION, "de")["code"] == "llm_no_model"


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
