"""The help and the tour of the interface: every step points at an element that the pages still mark."""

from __future__ import annotations

import re
from pathlib import Path

FRONTEND = Path(__file__).resolve().parent.parent / "frontend" / "src"
HELP = (FRONTEND / "lib" / "help.js").read_text(encoding="utf-8")


def _pages() -> dict[str, dict[str, list[str]]]:
    """The tour targets per page and language, as written in help.js."""
    pages: dict[str, dict[str, list[str]]] = {}
    parts = re.split(r'\n  "(/[a-z]+)": \{', HELP)
    for path, body in zip(parts[1::2], parts[2::2]):
        languages = re.split(r"\n    (de|en): \{", body)
        pages[path] = {lang: re.findall(r'target: "([a-z-]+)"', text) for lang, text in zip(languages[1::2], languages[2::2])}
    return pages


def test_every_page_has_help_in_both_languages_with_the_same_steps():
    pages = _pages()
    app = (FRONTEND / "App.svelte").read_text(encoding="utf-8")
    routes = set(re.findall(r'"(/[a-z]+)": [A-Z]', app))
    assert set(pages) == routes and len(routes) == 5
    for path, languages in pages.items():
        assert set(languages) == {"de", "en"}, path
        assert languages["de"] and languages["de"] == languages["en"], path


def test_every_tour_step_points_at_an_element_marked_in_the_interface():
    marked = set()
    for file in FRONTEND.rglob("*.svelte"):
        marked.update(re.findall(r'data-tour="([a-z-]+)"', file.read_text(encoding="utf-8")))
    targets = {t for languages in _pages().values() for steps in languages.values() for t in steps}
    assert targets <= marked, f"tour steps without an element: {sorted(targets - marked)}"
    assert marked <= targets, f"marked elements no step uses: {sorted(marked - targets)}"
