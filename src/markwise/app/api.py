"""What the interface may ask the core. The same object serves the app window (pywebview) and `markwise serve`.

Every public method returns {"data": ...} or {"error": "...", "code": "...", "params": {...}}, so that the
interface gets a message it can translate instead of a stack trace.
"""

from __future__ import annotations

import functools
import os
import sys
from pathlib import Path

from .. import __version__, catalog, settings as user_settings
from ..importer import import_pool
from ..module import EXAM_PATHS, MODULE_FILE, Module
from ..pool import POOL_FILE, Pool, PoolSettings


class Refusal(Exception):
    """A request the core turns down for a reason the person can fix; `code` names it for the interface."""

    def __init__(self, code: str, message: str, **params):
        super().__init__(message)
        self.code = code
        self.params = {k: str(v) for k, v in params.items()}


def _answer(method):
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        try:
            return {"data": method(*args, **kwargs)}
        except Refusal as exc:
            return {"error": str(exc), "code": exc.code, "params": exc.params}
        except Exception as exc:  # the interface shows the message; nothing may crash the window
            return {"error": str(exc.args[0]) if exc.args else exc.__class__.__name__}
    return wrapper


def _norm(path: str | Path) -> str:
    return str(Path(path).expanduser().resolve())


def _pool_entry(path: str) -> dict:
    folder = Path(path)
    if not (folder / POOL_FILE).exists():
        return {"path": path, "exists": False, "name": folder.name}
    pool = Pool.open(folder)
    return {"path": path, "exists": True, "name": pool.settings.name, "languages": pool.settings.languages,
            "questions": len(pool.question_files())}


def _module_entry(path: str) -> dict:
    folder = Path(path)
    if not (folder / MODULE_FILE).exists():
        return {"path": path, "exists": False, "name": folder.name, "short_name": "?", "pools": []}
    module = Module.open(folder)
    pools = [_pool_entry(str(module.pool_root(ref))) for ref in module.pools]
    return {"path": path, "exists": True, "name": module.name, "short_name": module.short_name,
            "regulations": module.regulations, "pools": pools}


def _remember_module(path: str, make_current: bool = True) -> None:
    current = user_settings.load()
    current.modules = [path] + [p for p in current.modules if p != path]
    if make_current:
        current.current_module = path
    user_settings.save(current)


def _check_pool_spec(spec: dict) -> Path:
    """Refuse a pool choice before anything is written, so that a refusal never leaves half a module behind."""
    mode, path = spec.get("mode"), (spec.get("path") or "").strip()
    if mode not in ("new", "existing", "import"):
        raise Refusal("pool_mode_unknown", f"unknown way to choose a pool: {mode!r}")
    if not path:
        raise Refusal("pool_folder_missing", "choose a folder for the question pool")
    folder = Path(path)
    if mode == "new":
        if (folder / POOL_FILE).exists():
            raise Refusal("pool_exists", f"{folder} already holds a question pool", path=folder)
        if not (spec.get("name") or "").strip():
            raise Refusal("pool_name_missing", "the question pool needs a name")
        if not [lang for lang in spec.get("languages") or [] if lang in ("de", "en")]:
            raise Refusal("pool_languages_missing", "choose at least one language")
    elif mode == "existing" and not (folder / POOL_FILE).exists():
        raise Refusal("pool_not_found", f"{folder} holds no question pool (pool.toml is missing)", path=folder)
    elif mode == "import" and not Path((spec.get("source") or "").strip()).is_file():
        raise Refusal("import_source_missing", "choose the pool.toml of the question bank to import")
    return folder


def _prepare_pool(spec: dict) -> tuple[Path, dict]:
    """Create, open or import the pool a module draws from. Returns its folder and what was done."""
    folder = _check_pool_spec(spec)
    if spec["mode"] == "new":
        languages = [lang for lang in spec["languages"] if lang in ("de", "en")]
        pool = Pool.create(folder, PoolSettings(name=spec["name"].strip(), languages=languages))
        return pool.root, {"pool": "created"}
    if spec["mode"] == "existing":
        return folder, {"pool": "opened"}
    report = import_pool(Path(spec["source"].strip()), folder)
    return folder, {"pool": "imported", "created": len(report.created), "conflicts": len(report.conflicts),
                    "problems": report.problems}


class Api:
    def __init__(self, window=None):
        self._window = window  # the pywebview window, for file dialogs; None when served over HTTP

    # --- basics ----------------------------------------------------------------------

    @_answer
    def info(self) -> dict:
        return {"version": __version__, "settings_file": str(user_settings.settings_file()),
                "dialogs": self._window is not None}

    @_answer
    def get_settings(self) -> dict:
        return user_settings.load().to_dict()

    @_answer
    def update_settings(self, changes: dict) -> dict:
        current = user_settings.load()
        current.update(changes)
        user_settings.save(current)
        return current.to_dict()

    @_answer
    def workspace(self) -> dict:
        current = user_settings.load()
        return {
            "modules": [_module_entry(p) for p in current.modules],
            "pools": [_pool_entry(p) for p in current.pools],
        }

    # --- folders -----------------------------------------------------------------------

    @_answer
    def pick_folder(self, start: str = "") -> str | None:
        """Windows folder dialog; None if cancelled. Only in the app window."""
        if self._window is None:
            raise Refusal("no_dialogs", "folder dialogs only work in the app window")
        import webview
        result = self._window.create_file_dialog(webview.FileDialog.FOLDER, directory=start or "")
        return _norm(result[0]) if result else None

    @_answer
    def pick_file(self, start: str = "", pattern: str = "pool.toml") -> str | None:
        if self._window is None:
            raise Refusal("no_dialogs", "file dialogs only work in the app window")
        import webview
        result = self._window.create_file_dialog(webview.FileDialog.OPEN, directory=start or "",
                                                 file_types=(f"Markwise ({pattern})", "All files (*.*)"))
        return _norm(result[0]) if result else None

    @_answer
    def inspect_folder(self, path: str) -> dict:
        """What a folder holds, so that the interface can say what opening it will do."""
        folder = Path(path)
        return {
            "path": _norm(folder) if path else "",
            "exists": folder.is_dir(),
            "module": (folder / MODULE_FILE).exists(),
            "pool": (folder / POOL_FILE).exists(),
            "empty": folder.is_dir() and not any(folder.iterdir()),
            "name": folder.name,
        }

    @_answer
    def reveal(self, path: str) -> None:
        """Show a folder in Windows Explorer."""
        if not Path(path).is_dir():
            raise Refusal("folder_missing", f"{path} does not exist", path=path)
        if sys.platform == "win32":
            os.startfile(path)  # noqa: S606 (opens Explorer on a folder the person chose)

    # --- modules -----------------------------------------------------------------------

    @_answer
    def create_module(self, spec: dict) -> dict:
        folder = Path((spec.get("folder") or "").strip())
        name, short_name = (spec.get("name") or "").strip(), (spec.get("short_name") or "").strip()
        if not name:
            raise Refusal("module_name_missing", "the module needs a name")
        if not short_name:
            raise Refusal("module_short_missing", "the module needs a short name")
        if not str(folder) or str(folder) == ".":
            raise Refusal("module_folder_missing", "choose a folder for the module")
        if (folder / MODULE_FILE).exists():
            raise Refusal("module_exists", f"{folder} already holds a module", path=folder)
        _check_pool_spec(spec.get("pool") or {})
        pool_root, outcome = _prepare_pool(spec["pool"])
        language = user_settings.load().language
        module = Module.create(folder, name, short_name, pools=[pool_root], exam_path=EXAM_PATHS.get(language, EXAM_PATHS["en"]))
        path = _norm(module.root)
        _remember_module(path)
        return {"module": _module_entry(path), **outcome}

    @_answer
    def open_module(self, path: str) -> dict:
        folder = Path(path)
        if not (folder / MODULE_FILE).exists():
            if (folder / POOL_FILE).exists():
                raise Refusal("is_pool", f"{folder} is a question pool, not a module", path=folder)
            raise Refusal("no_module", f"{folder} holds no module (module.toml is missing)", path=folder)
        path = _norm(folder)
        _remember_module(path)
        return _module_entry(path)

    @_answer
    def set_current_module(self, path: str) -> dict:
        current = user_settings.load()
        if path not in current.modules:
            raise Refusal("module_not_listed", f"{path} is not in the list of modules", path=path)
        current.current_module = path
        user_settings.save(current)
        return current.to_dict()

    @_answer
    def forget_module(self, path: str) -> dict:
        """Remove a module from the list; its folder and files stay untouched."""
        current = user_settings.load()
        current.modules = [p for p in current.modules if p != path]
        if current.current_module == path:
            current.current_module = current.modules[0] if current.modules else ""
        user_settings.save(current)
        return current.to_dict()

    @_answer
    def add_pool(self, module_path: str, pool_spec: dict) -> dict:
        module = Module.open(module_path)
        folder = _check_pool_spec(pool_spec)
        if folder.resolve() in [module.pool_root(ref) for ref in module.pools]:
            raise Refusal("pool_already_added", "the module already draws from this pool")
        pool_root, outcome = _prepare_pool(pool_spec)
        module.add_pool(pool_root)
        module.save()
        return {"module": _module_entry(module_path), **outcome}

    @_answer
    def remove_pool(self, module_path: str, pool_path: str) -> dict:
        """Detach a pool from the module; the pool itself stays untouched."""
        module = Module.open(module_path)
        module.remove_pool(pool_path)
        module.save()
        return _module_entry(module_path)

    # --- questions ---------------------------------------------------------------------

    @_answer
    def list_questions(self, module_path: str) -> dict:
        """All questions in the pools of a module, as rows for the list."""
        module = Module.open(module_path)
        language = user_settings.load().language
        pools, rows = [], []
        for ref in module.pools:
            root = module.pool_root(ref)
            if not (root / POOL_FILE).exists():
                pools.append({"path": str(root), "name": root.name, "exists": False})
                continue
            pool = Pool.open(root)
            pools.append({"path": str(root), "name": pool.settings.name, "exists": True,
                          "languages": pool.settings.languages, "concepts": pool.concepts()})
            rows.extend(catalog.rows(pool, language))
        return {"pools": pools, "questions": rows}

    @_answer
    def get_question(self, pool_path: str, qid: str) -> dict:
        return catalog.detail(Pool.open(pool_path), qid)

    @_answer
    def open_file(self, path: str) -> None:
        """Open a question file in the program Windows uses for YAML files. Only files inside an opened pool."""
        target = Path(path).resolve()
        if target.suffix not in (".yaml", ".toml") or not target.is_file():
            raise Refusal("file_missing", f"{path} is not a question file", path=path)
        allowed = []
        for module_path in user_settings.load().modules:
            if (Path(module_path) / MODULE_FILE).exists():
                module = Module.open(module_path)
                allowed.extend(module.pool_root(ref) for ref in module.pools)
        if not any(root == target or root in target.parents for root in allowed):
            raise Refusal("file_outside", f"{path} is not in a pool of an opened module", path=path)
        if sys.platform == "win32":
            os.startfile(target)  # noqa: S606 (a question file inside an opened pool)
