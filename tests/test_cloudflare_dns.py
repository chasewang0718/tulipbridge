"""Tests for optional Cloudflare DNS updates (mocked HTTP)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tulipbridge.cloudflare_dns import (
    cloudflare_update_lines,
    read_cached_ip,
    write_cached_ip,
)
from tulipbridge.paths import set_data_root


@pytest.fixture
def isolated_etc(tmp_path: Path):
    set_data_root(tmp_path)
    yield tmp_path
    set_data_root(None)


def test_cloudflare_lines_skips_without_public_ip() -> None:
    lines = cloudflare_update_lines(None)
    assert len(lines) == 1
    assert "no public ipv4" in lines[0].lower()


def test_cloudflare_lines_skips_without_env(
    isolated_etc: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.delenv("CLOUDFLARE_ZONE_ID", raising=False)
    monkeypatch.delenv("CLOUDFLARE_RECORD_NAME", raising=False)
    lines = cloudflare_update_lines("203.0.113.1")
    assert any("cloudflare.json" in L or "CLOUDFLARE" in L for L in lines)


def test_cloudflare_lines_uses_merged_json_file(
    isolated_etc: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CLOUDFLARE_API_TOKEN", raising=False)
    monkeypatch.delenv("CLOUDFLARE_ZONE_ID", raising=False)
    monkeypatch.delenv("CLOUDFLARE_RECORD_NAME", raising=False)
    etc = isolated_etc / "etc"
    etc.mkdir(parents=True)
    cfg = {
        "api_token": "tok",
        "zone_id": "zoneid",
        "record_name": "vpn.example.com",
    }
    etc.joinpath("cloudflare.json").write_text(
        json.dumps(cfg),
        encoding="utf-8",
    )

    with patch("tulipbridge.cloudflare_dns._request_json") as m:
        m.side_effect = [
            (True, {"result": [{"id": "rec"}]}),
            (True, {"success": True}),
        ]
        lines = cloudflare_update_lines("198.51.100.77")

    assert any("updated A record" in L for L in lines)
    assert read_cached_ip() == "198.51.100.77"


def test_cloudflare_lines_skips_when_cache_unchanged(
    isolated_etc: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "tok")
    monkeypatch.setenv("CLOUDFLARE_ZONE_ID", "zone")
    monkeypatch.setenv("CLOUDFLARE_RECORD_NAME", "vpn.example.com")
    write_cached_ip("198.51.100.1")
    lines = cloudflare_update_lines("198.51.100.1")
    assert any("unchanged" in L.lower() for L in lines)


def test_cloudflare_lines_updates_and_writes_cache(
    isolated_etc: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "tok")
    monkeypatch.setenv("CLOUDFLARE_ZONE_ID", "zone")
    monkeypatch.setenv("CLOUDFLARE_RECORD_NAME", "vpn.example.com")

    with patch("tulipbridge.cloudflare_dns._request_json") as m:
        m.side_effect = [
            (True, {"result": [{"id": "record-id"}]}),
            (True, {"success": True}),
        ]
        lines = cloudflare_update_lines("198.51.100.10")

    assert any("updated A record" in L for L in lines)
    assert read_cached_ip() == "198.51.100.10"


def test_cloudflare_lines_find_fails(
    isolated_etc: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "tok")
    monkeypatch.setenv("CLOUDFLARE_ZONE_ID", "zone")
    monkeypatch.setenv("CLOUDFLARE_RECORD_NAME", "vpn.example.com")

    with patch("tulipbridge.cloudflare_dns._request_json", return_value=(False, "API error")):
        lines = cloudflare_update_lines("198.51.100.2")

    assert any("failed to find" in L.lower() for L in lines)


def test_cmd_update_includes_cloudflare_section(
    isolated_etc: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from tulipbridge import cli

    etc = isolated_etc / "etc"
    etc.mkdir(parents=True)
    etc.joinpath("config.json").write_text('{"inbounds": []}', encoding="utf-8")

    with patch.object(cli, "fetch_public_ipv4", return_value="203.0.113.5"):
        code = cli._cmd_update(argparse.Namespace())

    assert code == 0
    out = capsys.readouterr().out
    assert "Cloudflare DNS" in out
