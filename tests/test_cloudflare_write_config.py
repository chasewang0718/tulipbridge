"""Tests for cloudflare-write-config and write_cloudflare_json_file."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from tulipbridge import cli
from tulipbridge.cloudflare_dns import write_cloudflare_json_file
from tulipbridge.paths import set_data_root


@pytest.fixture
def isolated_home(tmp_path: Path):
    set_data_root(tmp_path)
    yield tmp_path
    set_data_root(None)


def test_write_cloudflare_json_file_roundtrip(isolated_home: Path) -> None:
    path = write_cloudflare_json_file("my-token", "zone-id", "vpn.example.com")
    assert path.name == "cloudflare.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == {
        "api_token": "my-token",
        "zone_id": "zone-id",
        "record_name": "vpn.example.com",
    }
    if os.name == "posix":
        mode = stat.S_IMODE(Path(path).stat().st_mode)
        assert mode == 0o600


def test_cli_cloudflare_write_config(isolated_home: Path) -> None:
    code = cli.main(
        [
            "--data-dir",
            str(isolated_home),
            "cloudflare-write-config",
            "--token",
            "tok",
            "--zone-id",
            "z",
            "--record-name",
            "a.example.com",
        ]
    )
    assert code == 0
    cfg = isolated_home / "etc" / "cloudflare.json"
    assert cfg.is_file()
    assert json.loads(cfg.read_text(encoding="utf-8"))["record_name"] == "a.example.com"
