"""Optional help from a language model while writing questions: checking a question text and proposing distractors.

Off unless the examiner switches it on in the settings and enters an API key, which lives in the Windows
credential store, never in a file. Only the question's own texts are sent: question text, options and their
feedback. Nothing from exams, scans or participants ever goes to a provider. Every answer is a suggestion that
a person accepts or not.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from . import settings as user_settings

API = "https://api.openai.com/v1"
KEYRING_SERVICE = "Markwise"
KEYRING_USER = "openai"
ENV_VAR = "OPENAI_API_KEY"  # offered for use when no key is stored yet
TIMEOUT = 90

# Models that do not write text in a chat (images, speech, embeddings and the like) stay out of the choice.
NOT_FOR_TEXT = ("audio", "realtime", "transcribe", "tts", "image", "embedding", "search", "moderation", "dall-e",
                "whisper", "davinci", "babbage", "computer-use", "codex")

WRITING_RULES = """\
Rules for good multiple-choice questions in university exams:
- The question text holds the whole question: whoever reads only the text can already form the answer.
- One learning goal per question. Situations (reading code, interpreting measurements, choosing an approach,
  finding a mistake) are better than asking for definitions.
- No negations in the question text ("Which statement is not true?"); if unavoidable, emphasise the word; never
  a double negation.
- No hints in the question text that give an option away (same word, grammatical fit, singular against plural).
- Plain prose with normal capitalisation; code and identifiers in backticks.
- Options: all sound seriously meant, are about equally long, in the same register, without signal words
  ("always", "never", "only") and without polemics. Right or wrong is decided by the matter, not the tone.
- Distractors are real misconceptions: half-right statements with a wrong conclusion, true statements that do
  not answer the question asked, typical confusions of neighbouring concepts. No joke answers, no "all of the
  above", no "none of the above".
- Every option has a short feedback that says why it is right or wrong.
- The correct answer is not systematically the longest or the most cautious.
- Write in connected sentences; avoid chains of short sentences."""

LANGUAGE_NAMES = {"de": "German", "en": "English"}


class AssistError(Exception):
    """Something the examiner can fix or should know; `code` names it for the interface."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


# --- the key, in the Windows credential store ------------------------------------------


def get_key() -> str:
    import keyring
    return keyring.get_password(KEYRING_SERVICE, KEYRING_USER) or ""


def env_key() -> str:
    return os.environ.get(ENV_VAR, "").strip()


def masked(key: str) -> str:
    """Enough of a key to recognise it, never enough to use it."""
    return f"{key[:3]}…{key[-4:]}" if len(key) > 12 else "…"


def set_key(key: str) -> None:
    import keyring
    keyring.set_password(KEYRING_SERVICE, KEYRING_USER, key)


def remove_key() -> None:
    import keyring
    from keyring.errors import PasswordDeleteError
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_USER)
    except PasswordDeleteError:
        pass


# --- talking to the provider ------------------------------------------------------------


def _request(method: str, path: str, key: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(f"{API}{path}", data=data, method=method, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        detail = ""
        try:
            detail = json.loads(err.read().decode("utf-8")).get("error", {}).get("message", "")
        except Exception:
            pass
        if err.code == 401:
            raise AssistError("llm_key_invalid", "the API key was not accepted") from None
        if err.code == 429:
            raise AssistError("llm_quota", detail or "the provider refuses for now (limit or quota)") from None
        raise AssistError("llm_failed", detail or f"the provider answered with error {err.code}") from None
    except (urllib.error.URLError, TimeoutError) as err:
        raise AssistError("llm_network", f"the provider cannot be reached ({err})") from None


def list_models(key: str | None = None) -> list[str]:
    """The provider's models that write text, newest names first in alphabetical order."""
    key = key if key is not None else get_key()
    if not key:
        raise AssistError("llm_no_key", "no API key is stored")
    models = [m.get("id", "") for m in _request("GET", "/models", key).get("data", [])]
    usable = [m for m in models if (m.startswith("gpt") or m.startswith("o")) and not any(x in m for x in NOT_FOR_TEXT)]
    return sorted(usable, reverse=True)


def _ready() -> tuple[str, str]:
    """The key and model to use, or the reason why help is not available."""
    current = user_settings.load()
    if not current.llm_enabled:
        raise AssistError("llm_off", "help from a language model is switched off in the settings")
    key = get_key()
    if not key:
        raise AssistError("llm_no_key", "no API key is stored")
    if not current.llm_model:
        raise AssistError("llm_no_model", "no model is chosen in the settings")
    return key, current.llm_model


def _ask(system: str, user: str, schema_name: str, schema: dict) -> dict:
    key, model = _ready()
    answer = _request("POST", "/chat/completions", key, {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {"type": "json_schema", "json_schema": {"name": schema_name, "strict": True, "schema": schema}},
    })
    try:
        return json.loads(answer["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        raise AssistError("llm_failed", "the answer of the model could not be read") from None


def _question_text(fields: dict, lang: str) -> str:
    """The question as the model sees it: text, code and options with their feedback, in one language."""
    def pick(value):
        return value.get(lang, "") if isinstance(value, dict) else str(value or "")
    lines = [f"Question type: {fields.get('type', 'single')}", f"Question text:\n{pick(fields.get('stem'))}"]
    if fields.get("code"):
        lines.append(f"Code below the text:\n{fields['code']}")
    for option in fields.get("options") or []:
        mark = "correct" if option.get("correct") else "wrong"
        lines.append(f"Option {option.get('id')} ({mark}): {pick(option.get('text'))}"
                     + (f"\n  Feedback: {pick(option.get('feedback'))}" if pick(option.get("feedback")) else ""))
    return "\n".join(lines)


# --- the two kinds of help --------------------------------------------------------------


def check_stem(fields: dict, lang: str, answer_lang: str) -> dict:
    """Check the question text against the writing rules; returns findings and an improved text."""
    schema = {
        "type": "object", "additionalProperties": False, "required": ["findings", "suggestion"],
        "properties": {
            "findings": {"type": "array", "items": {"type": "string"}},
            "suggestion": {"type": "string"},
        },
    }
    system = (
        "You review questions for university exams and help the examiner improve them.\n\n" + WRITING_RULES +
        f"\n\nReview only the question text, using the options as context. List what breaks a rule or could be "
        f"misunderstood, each finding as one short sentence in {LANGUAGE_NAMES.get(answer_lang, 'English')}; an "
        f"empty list if nothing needs changing. Then give the improved question text in "
        f"{LANGUAGE_NAMES.get(lang, lang)}, keeping its meaning, its learning goal and its Markdown (backticks for "
        f"code); if nothing needs changing, return the text unchanged."
    )
    return _ask(system, _question_text(fields, lang), "stem_review", schema)


def distractors(fields: dict, languages: list[str], count: int, answer_lang: str) -> list[dict]:
    """Propose wrong options, with feedback, in every language of the pool."""
    texts = {"type": "object", "additionalProperties": False, "required": languages,
             "properties": {lang: {"type": "string"} for lang in languages}}
    schema = {
        "type": "object", "additionalProperties": False, "required": ["distractors"],
        "properties": {"distractors": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["text", "feedback", "misconception"],
            "properties": {"text": texts, "feedback": texts, "misconception": {"type": "string"}},
        }}},
    }
    names = ", ".join(f"{lang} ({LANGUAGE_NAMES.get(lang, lang)})" for lang in languages)
    system = (
        "You write wrong answer options (distractors) for multiple-choice questions in university exams.\n\n" +
        WRITING_RULES +
        f"\n\nPropose exactly {count} new distractors for the question. Each must be clearly wrong for someone who "
        f"understood the matter, yet plausible for someone with a typical misconception, and different from the "
        f"existing options. Match the existing options in length and register. Give the text and a one-sentence "
        f"feedback (why it is wrong) in each of these languages: {names}; the versions say the same. Name the "
        f"misconception behind each in a few words in {LANGUAGE_NAMES.get(answer_lang, 'English')}."
    )
    question = "\n\n".join(_question_text(fields, lang) for lang in languages[:1])
    answer = _ask(system, question, "distractors", schema)
    return answer.get("distractors", [])[:count]
