"""Round-trip YAML: read and write question files without losing comments, unknown fields or layout."""

from __future__ import annotations

import io
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import LiteralScalarString


def _yaml() -> YAML:
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.width = 4096  # never wrap long lines; question texts are edited by people
    yaml.indent(mapping=2, sequence=4, offset=2)
    return yaml


def load(path: Path) -> CommentedMap:
    with open(path, encoding="utf-8") as f:
        data = _yaml().load(f)
    if not isinstance(data, CommentedMap):
        raise ValueError("the file does not contain a YAML mapping")
    return data


def dumps(data: CommentedMap) -> str:
    buffer = io.StringIO()
    _yaml().dump(data, buffer)
    return buffer.getvalue()


def dump(data: CommentedMap, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write via a temporary file so that a crash never leaves half a question behind.
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(dumps(data), encoding="utf-8", newline="\n")
    tmp.replace(path)


def block(text: str) -> LiteralScalarString | str:
    """Multi-line text as a `|` block, short text as a plain scalar."""
    return LiteralScalarString(text) if "\n" in text else text
