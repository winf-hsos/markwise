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
