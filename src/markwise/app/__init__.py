"""The app window: the Svelte interface in a Windows WebView2 window, talking to the core through pywebview."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .. import settings as user_settings
from .api import Api

STATIC = Path(__file__).parent / "static"
ICON = Path(__file__).parent / "markwise.ico"
DEV_URL = "http://localhost:5173"
APP_ID = "HochschuleOsnabrueck.Markwise"


def run(dev: bool = False, debug: bool = False) -> None:
    import webview  # imported here so that the command line works without a window toolkit

    index = STATIC / "index.html"
    if not dev and not index.exists():
        raise FileNotFoundError(f"the interface is not built: {index} is missing (run npm run build in frontend/)")
    if sys.platform == "win32":
        # Group the window under its own taskbar entry with the Markwise icon instead of Python's.
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)

    webview.create_window(
        "Markwise", DEV_URL if dev else str(index), js_api=Api(),
        width=1320, height=860, min_size=(960, 640), background_color="#EDF0F3",
    )
    storage = user_settings.app_dir() / "webview"
    storage.mkdir(parents=True, exist_ok=True)
    webview.start(debug=debug, private_mode=False, storage_path=str(storage), icon=str(ICON))


def start_menu_folder() -> Path:
    import os
    return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs"


def create_shortcut(folder: Path | None = None) -> Path:
    """A Start menu entry that opens the window without a console (pythonw.exe -m markwise.app)."""
    if sys.platform != "win32":
        raise OSError("the shortcut is for Windows only")
    folder = folder or start_menu_folder()
    folder.mkdir(parents=True, exist_ok=True)
    link = folder / "Markwise.lnk"
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    target = pythonw if pythonw.exists() else Path(sys.executable)

    def ps(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    script = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut(" + ps(str(link)) + ");"
        "$s.TargetPath = " + ps(str(target)) + ";"
        "$s.Arguments = '-m markwise.app';"
        "$s.WorkingDirectory = " + ps(str(Path.home())) + ";"
        "$s.IconLocation = " + ps(str(ICON)) + ";"
        "$s.Description = 'Markwise: Papierklausuren';"
        "$s.Save()"
    )
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], check=True,
                   capture_output=True, text=True)
    return link
