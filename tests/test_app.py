"""Settings, the interface Api and the local HTTP bridge, without opening a window."""

from __future__ import annotations

import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from markwise import settings as user_settings
from markwise.app.api import Api
from markwise.app.server import make_handler
from markwise.module import Module
from markwise.pool import Pool, PoolSettings


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKWISE_HOME", str(tmp_path / "home"))
    return tmp_path / "home"


def test_settings_default_and_round_trip(home):
    assert user_settings.load().language == "de"
    s = user_settings.load()
    s.update({"language": "en", "examiner": "Test Examiner", "nav_collapsed": True})
    user_settings.save(s)
    again = user_settings.load()
    assert (again.language, again.examiner, again.nav_collapsed) == ("en", "Test Examiner", True)
    assert (home / "settings.toml").exists()


@pytest.mark.parametrize("changes", [{"language": "fr"}, {"colour": "red"}, {"nav_collapsed": "yes"}])
def test_settings_reject_bad_values(changes):
    with pytest.raises(ValueError):
        user_settings.Settings().update(changes)


def test_api_answers_data_or_error(tmp_path):
    api = Api()
    assert api.info()["data"]["version"]
    assert api.update_settings({"language": "en"})["data"]["language"] == "en"
    assert "error" in api.update_settings({"language": "fr"})


def test_api_workspace_lists_modules_and_their_pools(tmp_path):
    pool = Pool.create(tmp_path / "pool", PoolSettings(name="Invented Pool"))
    module = Module.create(tmp_path / "module", "Invented Module", "IM", pools=[pool.root])
    api = Api()
    api.update_settings({"modules": [str(module.root), str(tmp_path / "gone")]})
    modules = api.workspace()["data"]["modules"]
    assert modules[0]["name"] == "Invented Module" and modules[0]["pools"][0]["name"] == "Invented Pool"
    assert modules[1]["exists"] is False


@pytest.fixture
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Api()))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd.server_address[1]
    httpd.shutdown()
    httpd.server_close()


def post(port: int, method: str, args: list, headers: dict) -> tuple[int, dict]:
    request = urllib.request.Request(f"http://127.0.0.1:{port}/api/{method}", data=json.dumps({"args": args}).encode(),
                                     headers={"Content-Type": "application/json", **headers}, method="POST")
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read())


def test_server_calls_the_api(server):
    status, body = post(server, "update_settings", [{"examiner": "Test Examiner"}], {"X-Markwise": "1"})
    assert status == 200 and body["data"]["examiner"] == "Test Examiner"


def test_server_refuses_requests_without_header_or_from_other_hosts(server):
    assert post(server, "info", [], {})[0] == 403
    assert post(server, "info", [], {"X-Markwise": "1", "Host": "evil.example"})[0] == 403
    assert post(server, "_private", [], {"X-Markwise": "1"})[0] == 404


@pytest.mark.skipif(sys.platform != "win32", reason="Windows shortcut")
def test_shortcut_in_a_given_folder(tmp_path):
    from markwise.app import create_shortcut
    link = create_shortcut(tmp_path)
    assert link.exists() and link.suffix == ".lnk"


# --- step 2: modules and pools from the window ----------------------------------------


def test_create_module_with_a_new_pool(tmp_path):
    api = Api()
    api.update_settings({"language": "de"})
    result = api.create_module({"name": "Invented Module", "short_name": "IM", "folder": str(tmp_path / "module"),
                                "pool": {"mode": "new", "path": str(tmp_path / "pool"), "name": "Invented Pool",
                                         "languages": ["de"]}})["data"]
    assert result["pool"] == "created" and result["module"]["pools"][0]["name"] == "Invented Pool"
    module = Module.open(tmp_path / "module")
    assert module.exam_path.startswith("01 - Semester/{semester}/Klausur")
    settings = api.get_settings()["data"]
    assert settings["current_module"] == result["module"]["path"] and settings["modules"] == [result["module"]["path"]]


def test_a_refused_pool_leaves_no_module_behind(tmp_path):
    api = Api()
    answer = api.create_module({"name": "M", "short_name": "M", "folder": str(tmp_path / "module"),
                                "pool": {"mode": "existing", "path": str(tmp_path / "nothing")}})
    assert answer["code"] == "pool_not_found"
    assert not (tmp_path / "module").exists()


def test_create_module_importing_an_earlier_pool(tmp_path):
    from test_core import write_legacy
    legacy = write_legacy(tmp_path / "legacy")
    result = Api().create_module({"name": "M", "short_name": "M", "folder": str(tmp_path / "module"),
                                  "pool": {"mode": "import", "source": str(legacy), "path": str(tmp_path / "pool")}})["data"]
    assert result["pool"] == "imported" and result["created"] == 2


def test_open_module_tells_a_pool_from_a_module(tmp_path):
    pool = Pool.create(tmp_path / "pool", PoolSettings(name="P"))
    api = Api()
    assert api.open_module(str(pool.root))["code"] == "is_pool"
    assert api.open_module(str(tmp_path))["code"] == "no_module"
    Module.create(tmp_path / "module", "M", "M", pools=[pool.root])
    assert api.open_module(str(tmp_path / "module"))["data"]["name"] == "M"


def test_add_and_remove_pools_and_forget_modules(tmp_path):
    first = Pool.create(tmp_path / "first", PoolSettings(name="First"))
    Pool.create(tmp_path / "second", PoolSettings(name="Second"))
    module = Module.create(tmp_path / "module", "M", "M", pools=[first.root])
    api = Api()
    path = api.open_module(str(module.root))["data"]["path"]
    assert api.add_pool(path, {"mode": "existing", "path": str(first.root)})["code"] == "pool_already_added"
    added = api.add_pool(path, {"mode": "existing", "path": str(tmp_path / "second")})["data"]
    assert [p["name"] for p in added["module"]["pools"]] == ["First", "Second"]
    after = api.remove_pool(path, str(tmp_path / "first"))["data"]
    assert [p["name"] for p in after["pools"]] == ["Second"]
    assert api.forget_module(path)["data"]["modules"] == []
    assert (tmp_path / "module" / "module.toml").exists()  # forgetting never touches the folder


def test_dialogs_are_refused_without_a_window():
    assert Api().pick_folder()["code"] == "no_dialogs"
