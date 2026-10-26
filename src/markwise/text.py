"""Question texts are Markdown: a single line break is only a space, a blank line starts a new paragraph.

Earlier question banks wrapped their texts by hand at about 75 characters, so that the files read well. `unwrap`
joins such lines into one line per paragraph and keeps everything Markdown reads as structure: blank lines, list
items, fenced code, quotes, headings and hard breaks (two spaces or a backslash at the end of a line).
"""

from __future__ import annotations

import re

from ruamel.yaml.scalarstring import LiteralScalarString

LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+")
BLOCK_START = ("```", ">", "#", "|")


def unwrap(text: str) -> str:
    lines = str(text).strip("\n").split("\n")
    out: list[str] = []
    joinable = False  # whether the last line written is running text that a following line continues
    fence = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            fence = not fence
            out.append(line)
            joinable = False
            continue
        if fence or not stripped:
            out.append(line)
            joinable = False
            continue
        if stripped.startswith(BLOCK_START) or LIST_ITEM.match(line) or not joinable:
            out.append(line)
            joinable = not stripped.startswith(BLOCK_START)
            continue
        previous = out[-1]
        if previous.endswith("  ") or previous.endswith("\\"):
            out.append(stripped)  # a hard break the author meant
            continue
        out[-1] = previous.rstrip() + " " + stripped
    return "\n".join(line if line.endswith(("  ", "\\")) else line.rstrip() for line in out).rstrip()


# The fields of a question that hold running text, as {language: text} maps.
TEXT_FIELDS = ("stem", "expected", "marking_notes")
OPTION_TEXT_FIELDS = ("text", "feedback")


def _yaml_text(text: str):
    """Several paragraphs stay a readable block in the file; one paragraph is a plain line."""
    return LiteralScalarString(text + "\n") if "\n" in text else text


def unwrap_question(data) -> int:
    """Unwrap every running text of a question in place. Returns how many texts had lines wrapped by hand; a text
    that only loses the trailing line break of its block is rewritten as well, but not counted."""
    maps = [data.get(key) for key in TEXT_FIELDS]
    for option in data.get("options") or []:
        if isinstance(option, dict):
            maps += [option.get(key) for key in OPTION_TEXT_FIELDS]
    joined = 0
    for texts in maps:
        if not isinstance(texts, dict):
            continue
        for lang, value in list(texts.items()):
            if not isinstance(value, str) or "\n" not in value:
                continue
            new = unwrap(value)
            if str(_yaml_text(new)) == value:
                continue  # already one line per paragraph
            if new != value.strip("\n"):
                joined += 1
            if hasattr(texts, "insert"):
                # Taken out and put back at its place: ruamel would otherwise keep writing the old block style.
                position = list(texts).index(lang)
                del texts[lang]
                texts.insert(position, lang, _yaml_text(new))
            else:
                texts[lang] = _yaml_text(new)
    return joined
