"""Settings of one user on one computer: interface language, name, and the modules and pools opened recently.

They live in %APPDATA%\\Markwise\\settings.toml, never in a pool or module folder. MARKWISE_HOME overrides the
folder, for tests and for running several setups side by side.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

import tomli_w

LANGUAGES = ("de", "en")
THEMES = ("markwise", "hsos")  # colour schemes: the green of Markwise, the blue of Hochschule Osnabrück


def app_dir() -> Path:
    if os.environ.get("MARKWISE_HOME"):
        return Path(os.environ["MARKWISE_HOME"])
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    return Path(base) / "Markwise"


def settings_file() -> Path:
    return app_dir() / "settings.toml"


@dataclass
class Settings:
    language: str = "de"
    theme: str = "markwise"
    examiner: str = ""
    nav_collapsed: bool = False
    llm_enabled: bool = False  # help from a language model, off until the examiner switches it on
    llm_model: str = ""
    current_module: str = ""
    modules: list[str] = field(default_factory=list)  # module folders, most recent first
    pools: list[str] = field(default_factory=list)    # pool folders opened on their own, most recent first

    def to_dict(self) -> dict:
        return asdict(self)

    def update(self, changes: dict) -> None:
        known = {f.name for f in fields(self)}
        for key, value in changes.items():
            if key not in known:
                raise ValueError(f"unknown setting {key!r}")
            if key == "language" and value not in LANGUAGES:
                raise ValueError(f"language must be one of {', '.join(LANGUAGES)}")
            if key == "theme" and value not in THEMES:
                raise ValueError(f"theme must be one of {', '.join(THEMES)}")
            expected = type(getattr(self, key))
            if not isinstance(value, expected):
                raise ValueError(f"{key} must be of type {expected.__name__}")
            setattr(self, key, value)


def load() -> Settings:
    path = settings_file()
    if not path.exists():
        return Settings()
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    settings = Settings()
    known = {f.name for f in fields(settings)}
    for key, value in raw.items():
        if key in known:  # ignore settings from other versions instead of failing
            setattr(settings, key, value)
    return settings


def save(settings: Settings) -> None:
    path = settings_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomli_w.dumps(settings.to_dict()), encoding="utf-8")
