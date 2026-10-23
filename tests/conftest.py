"""Every test works with its own settings folder, never with the settings of the person running the tests."""

import pytest


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKWISE_HOME", str(tmp_path / "markwise-home"))
