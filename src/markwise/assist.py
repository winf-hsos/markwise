"""Optional help from a language model while writing questions: checking a question as a whole and completing it
(missing languages, feedback and wrong options), and proposing new numbers for a calculation.

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


def _missing_options(fields: dict, min_options: int) -> int:
    """How many options a choice question lacks to reach the pool's minimum."""
    if fields.get("type") == "free_text":
        return 0
    return max(0, min_options - len(fields.get("options") or []))


def review(fields: dict, languages: list[str], lang: str, answer_lang: str, min_options: int = 4) -> dict:
    """Check the question as a whole and complete it, in one go: findings, improved texts per field and language
    (including texts in the wrong or a missing language and missing feedback), and for a choice question with too
    few options as many new wrong options as it lacks."""
    names = _changeable(fields)
    needed = _missing_options(fields, min_options)
    texts = _texts_schema(languages)
    properties = {"findings": _findings_schema(names), "changes": _changes_schema(names, languages)}
    if needed:
        properties["new_options"] = {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["text", "feedback", "misconception"],
            "properties": {"text": texts, "feedback": texts, "misconception": {"type": "string"}},
        }}
    schema = {"type": "object", "additionalProperties": False, "required": list(properties), "properties": properties}

    if fields.get("type") == "free_text":
        task = (
            "Check the question as a whole: does the question text ask exactly what the expected answer answers, is "
            "it clear what and how much is expected, is the expected answer correct and complete, and do the marking "
            "notes let a second examiner award points the same way?"
        )
    else:
        task = (
            "Check the question as a whole: is the question text clear without the options; does every option "
            "answer the question that the text asks; is every option clear and unambiguous; are the options mutually "
            "exclusive (for single choice exactly one can be right); are exactly the options marked correct actually "
            "correct; does any option stand out by length, detail, wording, grammar or caution, so that it can be "
            "guessed without knowing the matter; are the distractors plausible; and does each feedback fit its "
            "option and whether it is right or wrong? Never change which options are correct; if a mark seems "
            "wrong, say so as a finding."
        )
    complete = (
        "Then complete the question: write every text that is missing in one of the languages, write the feedback "
        "an option lacks (why it is right or wrong), and fill an option whose text is empty with a plausible wrong "
        "answer if it is marked wrong."
    )
    if needed:
        complete += (
            f" The question has fewer options than the {min_options} it needs: propose exactly {needed} new wrong "
            f"options in `new_options`, each clearly wrong for someone who understood the matter yet plausible for "
            f"someone with a typical misconception, different from the existing options and like them in length and "
            f"register, with a one-sentence feedback, and name the misconception behind each in a few words in "
            f"{LANGUAGE_NAMES.get(answer_lang, 'English')}."
        )
    system = (
        "You review questions for university exams and help the examiner improve and complete them.\n\n" +
        WRITING_RULES + f"\n\n{LABELS}\n\n{task} The examiner is working on the "
        f"{LANGUAGE_NAMES.get(lang, lang)} version.\n\n{complete}\n\n"
        f"List what you find, including any text written in the wrong language, each as one short sentence in "
        f"{LANGUAGE_NAMES.get(answer_lang, 'English')}, naming in `about` the field it concerns (`question` for the "
        f"question as a whole); an empty list if nothing needs changing. In `changes`, give the complete new text of every field that should change or be filled, in "
        f"every one of these languages: {_named(languages)}, keeping the meaning, the learning goal and the Markdown "
        f"(backticks for code); a language version that is already right is returned unchanged. Fields are named "
        f"`stem`, `option.<id>.text`, `option.<id>.feedback`, `expected` and `marking_notes`."
    )
    answer = _ask(system, _question_text(fields, languages), "question_review", schema)
    result = {"findings": _findings(answer, names), "changes": _flatten(fields, answer.get("changes", []), names, languages),
              "new_options": []}
    for option in (answer.get("new_options") or [])[:needed]:
        text = {code: str((option.get("text") or {}).get(code) or "") for code in languages}
        if any(text.values()):
            result["new_options"].append({"text": text, "misconception": str(option.get("misconception") or ""),
                                          "feedback": {code: str((option.get("feedback") or {}).get(code) or "") for code in languages}})
    return result


def vary_numbers(fields: dict, languages: list[str], answer_lang: str) -> dict:
    """For a free-text calculation: other numbers in the task, with the expected answer and marking notes worked out
    again. Returns the proposed texts per field and language and the calculation, for the examiner to check."""
    if fields.get("type") != "free_text":
        raise AssistError("llm_not_free_text", "new numbers are proposed for free-text questions only")
    names = ["stem", "expected", "marking_notes"]
    schema = {
        "type": "object", "additionalProperties": False, "required": ["calculation", "findings", "changes"],
        "properties": {
            "calculation": {"type": "string"},
            "findings": _findings_schema(names),
            "changes": _changes_schema(names, languages),
        },
    }
    system = (
        "You help an examiner write a variant of a free-text exam question: the same task with other numbers.\n\n" +
        LABELS + "\n\n"
        "Choose new numbers for the task so that it tests exactly the same thing at the same difficulty: the same "
        "steps, the same units, values of a similar size and a result as easy or hard to state as in the original "
        "(no awkward rounding unless the original has it). Change nothing else in the question text. Then work out "
        "the new result yourself, step by step, and write the expected answer and the marking notes for the new "
        "numbers, in the same form and detail as the original; where the marking notes give points for steps, keep "
        "the points and adapt the steps.\n\n"
        f"Give the calculation, every step with its numbers and units, in {LANGUAGE_NAMES.get(answer_lang, 'English')}, "
        f"so that the examiner can check it. Propose the complete new texts for `stem`, `expected` and "
        f"`marking_notes` in each of these languages: {_named(languages)}; leave out a field that has no text in the "
        f"original. If the task has no numbers to vary, or a new result cannot be worked out reliably, say so as a "
        f"finding in one short sentence and propose no changes."
    )
    answer = _ask(system, _question_text(fields, languages), "number_variant", schema)
    return {"calculation": str(answer.get("calculation") or "").strip(), "findings": _findings(answer, names),
            "changes": _flatten(fields, answer.get("changes", []), names, languages)}
