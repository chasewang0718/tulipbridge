"""Tests for tulipbridge status_report."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tulipbridge.paths import set_data_root
from tulipbridge.status_report import build_status_lines, probe_tcp_local


@pytest.fixture
def isolated_home(tmp_path: Path):
    set_data_root(tmp_path)
    yield tmp_path
    set_data_root(None)


@pytest.fixture(autouse=True)
def _stub_wan_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid real HTTPS/DNS when exercising status_report."""
    monkeypatch.setattr(
        "tulipbridge.wan_dns_check.resolve_subscription_public_host",
        lambda _: None,
    )
    monkeypatch.setattr("tulipbridge.wan_dns_check.fetch_public_ipv4", lambda: None)
    monkeypatch.setattr(
        "tulipbridge.status_report.clash_memory_status_lines",
        lambda _cfg: [],
    )


def test_build_status_lines_no_config_no_pid(isolated_home: Path) -> None:
    lines = build_status_lines()
    text = "\n".join(lines)
    assert "Data directory:" in text
    assert "stopped (no PID file)" in text
    assert "No config" in text or "Run `tulipbridge init`" in text


def test_build_status_stale_pid(isolated_home: Path) -> None:
    (isolated_home / "sing-box.pid").write_text("424242\n", encoding="utf-8")
    with patch("tulipbridge.status_report.is_running", return_value=False):
        with patch("tulipbridge.status_report.read_pid", return_value=424242):
            lines = build_status_lines()
    text = "\n".join(lines)
    assert "stale PID file" in text
    assert "424242" in text


def test_build_status_running_tcp_probe(
    isolated_home: Path,
) -> None:
    etc = isolated_home / "etc"
    etc.mkdir(parents=True)
    cfg = {
        "inbounds": [
            {
                "type": "vless",
                "listen_port": 8443,
                "tls": {"server_name": "www.example.com"},
            }
        ]
    }
    (etc / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
    (isolated_home / "sing-box.pid").write_text("100\n", encoding="utf-8")

    with patch("tulipbridge.status_report.is_running", return_value=True):
        with patch("tulipbridge.status_report.read_pid", return_value=100):
            with patch(
                "tulipbridge.status_report.probe_tcp_local",
                return_value="listen_ok",
            ):
                lines = build_status_lines()

    text = "\n".join(lines)
    assert "running (PID 100)" in text
    assert "8443" in text
    assert "listen_ok" in text


def test_probe_tcp_local_refused() -> None:
    with patch("tulipbridge.status_report.socket.create_connection") as m:
        m.side_effect = ConnectionRefusedError()
        assert probe_tcp_local(65530) == "nothing_listening"


def test_probe_tcp_local_ok() -> None:
    fake_sock = object()

    class CM:
        def __enter__(self):
            return fake_sock

        def __exit__(self, *a: object):
            pass

    with patch("tulipbridge.status_report.socket.create_connection", return_value=CM()):
        assert probe_tcp_local(443) == "listen_ok"
