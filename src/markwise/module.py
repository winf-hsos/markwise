"""A module: module.toml in the examiner's folder for the module, pointing to its pools; exams live below it."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import tomli_w

from .pool import Pool

MODULE_FILE = "module.toml"
EXAM_FILE = "exam.toml"
# Default place for a new exam, relative to the module folder; follows the usual semester filing.
DEFAULT_EXAM_PATH = "01 - Semester/{semester}/Exam/{date} - {title}"


@dataclass
class Module:
    root: Path
    name: str
    short_name: str
    regulations: str = "hsos-at-2026"
    pools: list[str] = field(default_factory=list)  # as written in module.toml, relative to the module folder
    exam_path: str = DEFAULT_EXAM_PATH

    @classmethod
    def open(cls, path: Path | str) -> "Module":
        path = Path(path)
        root = path.parent if path.name == MODULE_FILE else path
        with open(root / MODULE_FILE, "rb") as f:
            raw = tomllib.load(f)
        return cls(
            root=root,
            name=raw["name"],
            short_name=raw.get("short_name", raw["name"]),
            regulations=raw.get("regulations", "hsos-at-2026"),
            pools=list(raw.get("pools", [])),
            exam_path=raw.get("exam_path", DEFAULT_EXAM_PATH),
        )

    @classmethod
    def create(cls, root: Path | str, name: str, short_name: str, pools: list[Path | str] = (),
               regulations: str = "hsos-at-2026") -> "Module":
        root = Path(root)
        if (root / MODULE_FILE).exists():
            raise FileExistsError(f"{root / MODULE_FILE} already exists")
        root.mkdir(parents=True, exist_ok=True)
        module = cls(root, name, short_name, regulations, [])
        for pool in pools:
            module.add_pool(pool)
        module.save()
        return module

    def save(self) -> None:
        data = {
            "name": self.name,
            "short_name": self.short_name,
            "regulations": self.regulations,
            "pools": self.pools,
            "exam_path": self.exam_path,
        }
        (self.root / MODULE_FILE).write_text(tomli_w.dumps(data), encoding="utf-8")

    def add_pool(self, pool: Path | str) -> None:
        """Store the pool relative to the module folder when possible, so both can move together."""
        pool_root = Pool.open(pool).root.resolve()
        try:
            ref = os.path.relpath(pool_root, self.root.resolve())
        except ValueError:  # another drive on Windows
            ref = str(pool_root)
        ref = Path(ref).as_posix()
        if ref not in self.pools:
            self.pools.append(ref)

    def open_pools(self) -> list[Pool]:
        return [Pool.open(((self.root / ref) if not Path(ref).is_absolute() else Path(ref)).resolve()) for ref in self.pools]

    def exams(self) -> list[Path]:
        """Every folder below the module folder that holds an exam.toml."""
        return sorted(p.parent for p in self.root.rglob(EXAM_FILE))

    def new_exam_folder(self, semester: str, date: str, title: str) -> Path:
        return self.root / self.exam_path.format(semester=semester, date=date, title=title)
