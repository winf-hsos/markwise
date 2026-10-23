"""Optional help from a language model while writing questions: checking a question text or the whole question,
translating it into the other languages of the pool and proposing distractors.

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




def _named(languages: list[str]) -> str:
    return ", ".join(f"{lang} ({LANGUAGE_NAMES.get(lang, lang)})" for lang in languages)


LABELS = (
    "Every text is labelled with the language it must be written in, for example [de] for German. A text written "
    "in another language than its label (German under [en], say) is a mistake: report it as a finding and propose "
    "the text in the right language. A text missing in one of the languages is proposed as well, translated from "
    "the others. All language versions of a field say the same."
)


def _question_text(fields: dict, languages: list[str]) -> str:
    """The question as the model sees it: text, code, options with their feedback or the expected answer, each text
    in every language of the pool and labelled with the language it must be written in."""
    def texts(value, indent="  "):
        if not isinstance(value, dict):
            return f"{indent}{value or ''}"
        return "\n".join(f"{indent}[{lang}] {value.get(lang, '') or '(missing)'}" for lang in languages)
    lines = [f"Question type: {fields.get('type', 'single')}", f"Question text:\n{texts(fields.get('stem'))}"]
    if fields.get("code"):
        lines.append(f"Code below the text (the same in every language):\n{fields['code']}")
    for option in fields.get("options") or []:
        mark = "correct" if option.get("correct") else "wrong"
        lines.append(f"Option {option.get('id')} ({mark}):\n{texts(option.get('text'))}")
        if any(str((option.get("feedback") or {}).get(lang) or "").strip() for lang in languages):
            lines.append(f"  Feedback on option {option.get('id')}:\n{texts(option.get('feedback'), '    ')}")
    if fields.get("type") == "free_text":
        lines.append(f"Expected answer:\n{texts(fields.get('expected'))}")
        lines.append(f"Marking notes:\n{texts(fields.get('marking_notes'))}")
    return "\n".join(lines)


def _changeable(fields: dict) -> list[str]:
    """The text fields a suggestion may concern."""
    if fields.get("type") == "free_text":
        return ["stem", "expected", "marking_notes"]
    names = ["stem"]
    for option in fields.get("options") or []:
        names += [f"option.{option.get('id')}.text", f"option.{option.get('id')}.feedback"]
    return names


def _current(fields: dict, name: str, lang: str) -> str:
    if name.startswith("option."):
        _, oid, part = name.split(".")
        option = next((o for o in fields.get("options") or [] if o.get("id") == oid), {})
        value = option.get(part)
    else:
        value = fields.get(name)
    return value.get(lang, "") if isinstance(value, dict) else str(value or "")


def _texts_schema(languages: list[str]) -> dict:
    return {"type": "object", "additionalProperties": False, "required": languages,
            "properties": {lang: {"type": "string"} for lang in languages}}


def _findings_schema(names: list[str]) -> dict:
    return {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["about", "text"],
        "properties": {"about": {"type": "string", "enum": ["question"] + names}, "text": {"type": "string"}},
    }}


def _changes_schema(names: list[str], languages: list[str]) -> dict:
    return {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["field", "texts"],
        "properties": {"field": {"type": "string", "enum": names}, "texts": _texts_schema(languages)},
    }}


def _flatten(fields: dict, proposed: list, names: list[str], languages: list[str]) -> list[dict]:
    """Proposed texts per field and language, keeping only those that differ from what the question has."""
    changes, seen = [], set()
    for change in proposed:
        name = change.get("field")
        if name not in names or name in seen:
            continue
        seen.add(name)
        for lang in languages:
            text = str((change.get("texts") or {}).get(lang) or "").strip()
            before = _current(fields, name, lang)
            if text and text != before.strip():
                changes.append({"field": name, "lang": lang, "text": text, "before": before})
    return changes


def _findings(answer: dict, names: list[str]) -> list[dict]:
    return [f for f in answer.get("findings", []) if f.get("about") in ["question"] + names and f.get("text", "").strip()]


# --- the kinds of help -----------------------------------------------------------------


def check_stem(fields: dict, languages: list[str], lang: str, answer_lang: str) -> dict:
    """Check the question text against the writing rules; returns findings and the improved text in every language
    of the pool, so that the versions stay alike."""
    schema = {
        "type": "object", "additionalProperties": False, "required": ["findings", "suggestion"],
        "properties": {"findings": {"type": "array", "items": {"type": "string"}}, "suggestion": _texts_schema(languages)},
    }
    system = (
        "You review questions for university exams and help the examiner improve them.\n\n" + WRITING_RULES +
        f"\n\n{LABELS}\n\nReview only the question text, using the options as context; the examiner is working on "
        f"the {LANGUAGE_NAMES.get(lang, lang)} version. List what breaks a rule, could be misunderstood or is written "
        f"in the wrong language, each finding as one short sentence in {LANGUAGE_NAMES.get(answer_lang, 'English')}; "
        f"an empty list if nothing needs changing. Then give the improved question text in each of these languages: "
        f"{_named(languages)}, keeping its meaning, its learning goal and its Markdown (backticks for code). A "
        f"version that needs no change is returned unchanged."
    )
    answer = _ask(system, _question_text(fields, languages), "stem_review", schema)
    suggestion = {code: str((answer.get("suggestion") or {}).get(code) or "") for code in languages}
    return {"findings": [str(f) for f in answer.get("findings", []) if str(f).strip()], "suggestion": suggestion}


def review_question(fields: dict, languages: list[str], lang: str, answer_lang: str) -> dict:
    """Check the question as a whole, text and answers together; returns findings and proposed new texts per field
    and language."""
    names = _changeable(fields)
    schema = {
        "type": "object", "additionalProperties": False, "required": ["findings", "changes"],
        "properties": {"findings": _findings_schema(names), "changes": _changes_schema(names, languages)},
    }
    if fields.get("type") == "free_text":
        task = (
            "Review the question as a whole: does the question text ask exactly what the expected answer answers, is "
            "it clear what and how much is expected, is the expected answer correct and complete, and do the marking "
            "notes let a second examiner award points the same way?"
        )
    else:
        task = (
            "Review the question as a whole: does every option answer the question that the text asks; is every "
            "option clear and unambiguous; are the options mutually exclusive (for single choice exactly one can be "
            "right); are exactly the options marked correct actually correct; does any option stand out by length, "
            "detail, wording, grammar or caution, so that it can be guessed without knowing the matter; are the "
            "distractors plausible; and does each feedback fit its option and whether it is right or wrong? Never "
            "change which options are correct; if a mark seems wrong, say so as a finding."
        )
    system = (
        "You review questions for university exams and help the examiner improve them.\n\n" + WRITING_RULES +
        f"\n\n{LABELS}\n\n{task} The examiner is working on the {LANGUAGE_NAMES.get(lang, lang)} version.\n\n"
        f"List what you find, each as one short sentence in {LANGUAGE_NAMES.get(answer_lang, 'English')}, naming in "
        f"`about` the field it concerns (`question` for the question as a whole); an empty list if nothing needs "
        f"changing. Then propose new texts only for the fields that should change, each with its complete new text "
        f"in every one of these languages: {_named(languages)}, keeping the meaning, the learning goal and the "
        f"Markdown (backticks for code). Fields are named `stem`, `option.<id>.text`, `option.<id>.feedback`, "
        f"`expected` and `marking_notes`."
    )
    answer = _ask(system, _question_text(fields, languages), "question_review", schema)
    return {"findings": _findings(answer, names), "changes": _flatten(fields, answer.get("changes", []), names, languages)}


def translate(fields: dict, languages: list[str], source: str, answer_lang: str) -> dict:
    """Translate the question from one language of the pool into the others; returns proposed texts per field and
    language, and findings such as a source text written in the wrong language."""
    targets = [lang for lang in languages if lang != source]
    if not targets:
        raise AssistError("llm_one_language", "the pool has only one language")
    names = [name for name in _changeable(fields) if _current(fields, name, source).strip()]
    if not names:
        raise AssistError("llm_nothing_to_translate", f"the question has no text in {source} yet")
    schema = {
        "type": "object", "additionalProperties": False, "required": ["findings", "translations"],
        "properties": {"findings": _findings_schema(names), "translations": _changes_schema(names, targets)},
    }
    system = (
        "You translate questions for university exams.\n\n" + LABELS + "\n\n"
        f"Translate every text of the question from {LANGUAGE_NAMES.get(source, source)} into {_named(targets)}: "
        f"each of these fields: {', '.join(f'`{n}`' for n in names)}. Translate faithfully, in the register of a "
        f"university exam and with the usual technical terms of the subject in the target language; keep the "
        f"Markdown and leave code, identifiers in backticks, numbers and units as they are. The translation must not "
        f"make an option easier or harder to recognise than in the original, for example by length or by a word "
        f"that echoes the question text. Where an existing translation is already right, return it unchanged. "
        f"If a {LANGUAGE_NAMES.get(source, source)} text is itself in another language, or something cannot be "
        f"translated faithfully, say so as a finding in one short sentence in "
        f"{LANGUAGE_NAMES.get(answer_lang, 'English')}; otherwise the list of findings is empty."
    )
    answer = _ask(system, _question_text(fields, languages), "translation", schema)
    return {"findings": _findings(answer, names), "changes": _flatten(fields, answer.get("translations", []), names, targets)}


def distractors(fields: dict, languages: list[str], count: int, answer_lang: str) -> list[dict]:
    """Propose wrong options, with feedback, in every language of the pool."""
    texts = _texts_schema(languages)
    schema = {
        "type": "object", "additionalProperties": False, "required": ["distractors"],
        "properties": {"distractors": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["text", "feedback", "misconception"],
            "properties": {"text": texts, "feedback": texts, "misconception": {"type": "string"}},
        }}},
    }
    system = (
        "You write wrong answer options (distractors) for multiple-choice questions in university exams.\n\n" +
        WRITING_RULES +
        f"\n\nThe question below shows each text in every language of the pool, labelled with its language.\n\n"
        f"Propose exactly {count} new distractors for the question. Each must be clearly wrong for someone who "
        f"understood the matter, yet plausible for someone with a typical misconception, and different from the "
        f"existing options. Match the existing options in length and register. Give the text and a one-sentence "
        f"feedback (why it is wrong) in each of these languages: {_named(languages)}; each version is written in "
        f"its own language, even where the question itself still lacks it, and the versions say the same. Name the "
        f"misconception behind each in a few words in {LANGUAGE_NAMES.get(answer_lang, 'English')}."
    )
    answer = _ask(system, _question_text(fields, languages), "distractors", schema)
    return answer.get("distractors", [])[:count]
