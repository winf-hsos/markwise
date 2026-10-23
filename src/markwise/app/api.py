"""What the interface may ask the core. The same object serves the app window (pywebview) and `markwise serve`.

Every public method returns {"data": ...} or {"error": "..."}, so that the interface gets a readable message
instead of a stack trace.
"""

from __future__ import annotations

import functools
from pathlib import Path

from .. import __version__, settings as user_settings
from ..module import MODULE_FILE, Module
from ..pool import POOL_FILE, Pool


def _answer(method):
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        try:
            return {"data": method(*args, **kwargs)}
        except Exception as exc:  # the interface shows the message; nothing may crash the window
            return {"error": str(exc.args[0]) if exc.args else exc.__class__.__name__}
    return wrapper


def _pool_entry(path: str) -> dict:
    folder = Path(path)
    if not (folder / POOL_FILE).exists():
        return {"path": path, "exists": False, "name": folder.name}
    pool = Pool.open(folder)
    return {"path": path, "exists": True, "name": pool.settings.name, "languages": pool.settings.languages}


def _module_entry(path: str) -> dict:
    folder = Path(path)
    if not (folder / MODULE_FILE).exists():
        return {"path": path, "exists": False, "name": folder.name, "short_name": "?", "pools": []}
    module = Module.open(folder)
    pools = []
    for ref in module.pools:
        target = (folder / ref).resolve() if not Path(ref).is_absolute() else Path(ref)
        pools.append(_pool_entry(str(target)))
    return {"path": path, "exists": True, "name": module.name, "short_name": module.short_name,
            "regulations": module.regulations, "pools": pools}


class Api:
    @_answer
    def info(self) -> dict:
        return {"version": __version__, "settings_file": str(user_settings.settings_file())}

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
