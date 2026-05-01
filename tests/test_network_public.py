"""Tests for public IPv4 lookup (mocked HTTP)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tulipbridge.network_public import (
    fetch_public_ipv4,
    ipv4_lookup_note,
)
from tulipbridge.paths import set_data_root


class _FakeResp:
    def __init__(self, code: int, body: str) -> None:
        self.status = code
        self._body = body.encode("utf-8")

    def getcode(self) -> int:
        return self.status

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResp:
        return self

    def __exit__(self, *args: object) -> None:
        pass


def test_fetch_public_ipv4_ok_first_url() -> None:
    fake = _FakeResp(200, "203.0.113.45\n")
    with patch("tulipbridge.network_public.urlopen", return_value=fake):
        assert fetch_public_ipv4(timeout=1.0) == "203.0.113.45"


def test_fetch_public_ipv4_fallback_second_url() -> None:
    def side_effect(*_a: object, **_k: object) -> _FakeResp:
        if not hasattr(side_effect, "n"):
            side_effect.n = 0  # type: ignore[attr-defined]
        side_effect.n += 1  # type: ignore[attr-defined]
        if side_effect.n == 1:
            raise TimeoutError()
        return _FakeResp(200, "198.51.100.2")

    with patch("tulipbridge.network_public.urlopen", side_effect=side_effect):
        assert fetch_public_ipv4(timeout=1.0) == "198.51.100.2"


def test_fetch_public_ipv4_returns_none_on_bad_body() -> None:
    fake = _FakeResp(200, "not-an-ip")
    with patch("tulipbridge.network_public.urlopen", return_value=fake):
        assert fetch_public_ipv4(timeout=1.0) is None


def test_fetch_public_ipv4_returns_none_on_non_200() -> None:
    fake = _FakeResp(500, "203.0.113.1")
    with patch("tulipbridge.network_public.urlopen", return_value=fake):
        assert fetch_public_ipv4(timeout=1.0) is None


def test_ipv4_lookup_note_cgnat_range() -> None:
    assert ipv4_lookup_note("100.64.0.1") is not None
    assert ipv4_lookup_note("203.0.113.1") is None


@pytest.fixture
def isolated_home(tmp_path: Path):
    set_data_root(tmp_path)
    yield tmp_path
    set_data_root(None)


def test_cmd_update_prints_ip_and_ports(
    isolated_home: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from tulipbridge import cli

    etc = isolated_home / "etc"
    etc.mkdir(parents=True)
    cfg = {
        "inbounds": [
            {
                "type": "vless",
                "listen_port": 9443,
                "tls": {"server_name": "www.example.com"},
            }
        ]
    }
    (etc / "config.json").write_text(json.dumps(cfg), encoding="utf-8")

    with patch.object(cli, "fetch_public_ipv4", return_value="203.0.113.10"):
        code = cli._cmd_update(argparse.Namespace())

    assert code == 0
    out = capsys.readouterr().out
    assert "203.0.113.10" in out
    assert "9443" in out
    assert "DDNS" in out or "Cloudflare" in out
