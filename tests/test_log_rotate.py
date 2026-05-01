"""Tests for sing-box log rotation."""

from __future__ import annotations

import pytest

from tulipbridge.log_rotate import rotate_singbox_log
from tulipbridge.paths import set_data_root, singbox_log_path


@pytest.fixture
def isolated_home(tmp_path):
    set_data_root(tmp_path)
    yield tmp_path
    set_data_root(None)


def test_rotate_when_over_limit(isolated_home, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TULIPBRIDGE_LOG_MAX_BYTES", raising=False)
    log = singbox_log_path()
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("x" * 5000, encoding="utf-8")

    did, msg = rotate_singbox_log(max_bytes=4000)
    assert did is True
    assert "Rotated" in msg
    assert singbox_log_path().is_file()
    assert singbox_log_path().stat().st_size == 0
    backup = singbox_log_path().with_suffix(singbox_log_path().suffix + ".1")
    assert backup.is_file()
    assert backup.stat().st_size == 5000


def test_no_rotate_under_limit(isolated_home) -> None:
    log = singbox_log_path()
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("small", encoding="utf-8")
    did, msg = rotate_singbox_log(max_bytes=10000)
    assert did is False
    assert "no rotation" in msg.lower() or "limit" in msg.lower()


def test_env_max_bytes(monkeypatch: pytest.MonkeyPatch, isolated_home) -> None:
    monkeypatch.setenv("TULIPBRIDGE_LOG_MAX_BYTES", "5000")
    log = singbox_log_path()
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("x" * 6000, encoding="utf-8")
    did, _msg = rotate_singbox_log()
    assert did is True
