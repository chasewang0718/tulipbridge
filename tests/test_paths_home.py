"""Resolution order for get_tulipbridge_home (cwd tulipbridge-data)."""

from __future__ import annotations

from pathlib import Path

from tulipbridge.paths import get_tulipbridge_home, set_data_root

_LOCAL_DATA = "tulipbridge-data"


def test_cwd_tulipbridge_data_used_when_present(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TULIPBRIDGE_HOME", raising=False)
    set_data_root(None)
    local_root = tmp_path / _LOCAL_DATA
    local_root.mkdir()
    monkeypatch.chdir(tmp_path)
    assert get_tulipbridge_home() == local_root.resolve()


def test_default_dot_tulipbridge_when_no_local_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TULIPBRIDGE_HOME", raising=False)
    set_data_root(None)
    monkeypatch.chdir(tmp_path)
    assert get_tulipbridge_home() == (Path.home() / ".tulipbridge").resolve()


def test_override_root_wins_over_cwd_data(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TULIPBRIDGE_HOME", raising=False)
    (tmp_path / _LOCAL_DATA).mkdir()
    custom = tmp_path / "other-data"
    custom.mkdir()
    set_data_root(custom)
    monkeypatch.chdir(tmp_path)
    assert get_tulipbridge_home() == custom.resolve()
    set_data_root(None)
