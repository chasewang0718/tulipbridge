"""Tests for optional Clash API memory fetch."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from tulipbridge.clash_memory import clash_memory_status_lines


def test_clash_memory_skips_without_experimental() -> None:
    assert clash_memory_status_lines({}) == []
    assert clash_memory_status_lines({"experimental": {}}) == []


def test_clash_memory_fetches_json() -> None:
    cfg = {
        "experimental": {
            "clash_api": {
                "external_controller": "127.0.0.1:9090",
                "secret": "abc",
            }
        }
    }
    payload = {"inuse": 1, "total": 100}
    raw = json.dumps(payload).encode("utf-8")

    with patch("tulipbridge.clash_memory.urlopen") as uo:
        cm = MagicMock()
        cm.__enter__.return_value.read.return_value = raw
        cm.__enter__.return_value.getcode = MagicMock(return_value=200)
        cm.__enter__.return_value.status = 200
        uo.return_value = cm

        lines = clash_memory_status_lines(cfg)

    text = "\n".join(lines)
    assert "Clash API" in text
    assert "inuse" in text or "1" in text


def test_clash_memory_unreachable() -> None:
    cfg = {
        "experimental": {
            "clash_api": {
                "external_controller": "127.0.0.1:1",
                "secret": "",
            }
        }
    }
    with patch(
        "tulipbridge.clash_memory.urlopen",
        side_effect=URLError(OSError("refused")),
    ):
        lines = clash_memory_status_lines(cfg)
    assert any("unreachable" in L.lower() for L in lines)
