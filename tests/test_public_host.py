"""Tests for subscription public host resolution and persistence."""

from __future__ import annotations

import pytest

from tulipbridge.paths import set_data_root
from tulipbridge.public_host import (
    read_stored_public_host,
    resolve_subscription_public_host,
    subscription_refresh_hint_lines,
    write_stored_public_host,
)


@pytest.fixture
def isolated_home(tmp_path):
    set_data_root(tmp_path)
    yield tmp_path
    set_data_root(None)


def test_resolve_prefers_cli_over_file_and_env(
    isolated_home,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_stored_public_host("stored.example.com")
    monkeypatch.setenv("CLOUDFLARE_RECORD_NAME", "env.example.com")
    assert resolve_subscription_public_host("cli.example.com") == "cli.example.com"


def test_resolve_uses_file_when_no_cli(isolated_home) -> None:
    write_stored_public_host("file.example.com")
    assert resolve_subscription_public_host(None) == "file.example.com"


def test_resolve_uses_cloudflare_record_when_no_file(
    isolated_home,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLOUDFLARE_RECORD_NAME", "ddns.example.com")
    assert resolve_subscription_public_host(None) == "ddns.example.com"


def test_resolve_returns_none_when_empty(isolated_home, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLOUDFLARE_RECORD_NAME", raising=False)
    assert resolve_subscription_public_host(None) is None
    assert resolve_subscription_public_host("") is None
    assert resolve_subscription_public_host("  ") is None


def test_read_stored_roundtrip(isolated_home) -> None:
    assert read_stored_public_host() is None
    write_stored_public_host(" 10.0.0.1 ")
    assert read_stored_public_host() == "10.0.0.1"


def test_subscription_refresh_hint_when_default_available(
    isolated_home,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CLOUDFLARE_RECORD_NAME", "x.example.com")
    lines = subscription_refresh_hint_lines()
    assert any("tulipbridge links" in L and "YOUR_HOST" not in L for L in lines)


def test_subscription_refresh_hint_when_no_default(isolated_home, monkeypatch) -> None:
    monkeypatch.delenv("CLOUDFLARE_RECORD_NAME", raising=False)
    lines = subscription_refresh_hint_lines()
    assert any("YOUR_HOST" in L for L in lines)
