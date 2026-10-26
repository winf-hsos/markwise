"""Formulas in question texts: LaTeX math between dollar signs, as Markdown with Pandoc and Quarto reads it.

`$E = mc^2$` stands in the running text, `$$ … $$` on lines of its own is set apart. So that a dollar sign as a
character does not start a formula by chance, the rules of Pandoc apply: the opening `$` must be followed right
away by something other than a space, the closing one preceded by something other than a space and not followed by
a digit. `\\$` is a dollar sign as such, and code between backticks never holds a formula. The interface follows
the same rules (frontend/src/lib/formulas.js), so that a text reads alike in the window and in the booklet.
"""

from __future__ import annotations

import re

TEXT, INLINE, DISPLAY, CODE = "text", "inline", "display", "code"


def split(text: str) -> list[tuple[str, str]]:
    """The text in pieces: running text (with `\\$` already turned into `$`), code spans with their backticks,
    inline formulas and formulas set apart, each without its dollar signs."""
    out: list[tuple[str, str]] = []
    buffer: list[str] = []
    i, n = 0, len(text)

    def flush():
        if buffer:
            out.append((TEXT, "".join(buffer)))
            buffer.clear()

    while i < n:
        c = text[i]
        if c == "\\" and i + 1 < n and text[i + 1] == "$":
            buffer.append("$")
            i += 2
            continue
        if c == "`":
            end = text.find("`", i + 1)
            if end > i + 1:
                flush()
                out.append((CODE, text[i:end + 1]))
                i = end + 1
                continue
        if text.startswith("$$", i):
            end = text.find("$$", i + 2)
            if end > i + 2 and text[i + 2:end].strip():
                flush()
                out.append((DISPLAY, text[i + 2:end].strip()))
                i = end + 2
                continue
        if c == "$" and i + 1 < n and not text[i + 1].isspace() and text[i + 1] != "$":
            end = _closing(text, i + 1)
            if end is not None:
                flush()
                out.append((INLINE, text[i + 1:end]))
                i = end + 1
                continue
        buffer.append(c)
        i += 1
    flush()
    return out


def _closing(text: str, start: int) -> int | None:
    """The closing dollar of an inline formula that opens before `start`, on the same line."""
    j = start
    while j < len(text):
        c = text[j]
        if c == "\n" and text[j + 1:j + 2] == "\n":
            return None  # a formula does not run over a paragraph break
        if c == "\\":
            j += 2
            continue
        if c == "$":
            if not text[j - 1].isspace() and not text[j + 1:j + 2].isdigit():
                return j
            return None
        j += 1
    return None


def formulas(text: str) -> list[tuple[str, str]]:
    """The formulas of a text: (kind, LaTeX)."""
    return [(kind, part) for kind, part in split(text or "") if kind in (INLINE, DISPLAY)]


def problems(latex: str) -> list[str]:
    """What keeps a formula from being read, as short codes: unbalanced braces, an environment left open."""
    found = []
    depth = 0
    i = 0
    while i < len(latex):
        c = latex[i]
        if c == "\\":
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth < 0:
                break
        i += 1
    if depth != 0:
        found.append("braces")
    begins = re.findall(r"\\begin\{(\w+\*?)\}", latex)
    ends = re.findall(r"\\end\{(\w+\*?)\}", latex)
    if sorted(begins) != sorted(ends):
        found.append("environment")
    if re.search(r"(?<!\\)\$", latex):
        found.append("dollar")
    return found
