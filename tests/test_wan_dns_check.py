"""Tests for WAN/DNS vs outbound IPv4 (status hook)."""

from __future__ import annotations

import socket
from unittest.mock import patch

import pytest

from tulipbridge.paths import set_data_root
from tulipbridge.wan_dns_check import build_wan_dns_lines


@pytest.fixture
def isolated_home(tmp_path):
    set_data_root(tmp_path)
    yield tmp_path
    set_data_root(None)


def test_wan_dns_skips_when_no_host(isolated_home, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tulipbridge.wan_dns_check.resolve_subscription_public_host",
        lambda _: None,
    )
    lines = build_wan_dns_lines()
    assert any("none" in L.lower() and "public_host" in L for L in lines)


def test_wan_dns_literal_match(isolated_home, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tulipbridge.wan_dns_check.resolve_subscription_public_host",
        lambda _: "198.51.100.10",
    )
    monkeypatch.setattr(
        "tulipbridge.wan_dns_check.fetch_public_ipv4",
        lambda: "198.51.100.10",
    )
    lines = build_wan_dns_lines()
    text = "\n".join(lines)
    assert "Match" in text
    assert "198.51.100.10" in text


def test_wan_dns_literal_mismatch(isolated_home, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tulipbridge.wan_dns_check.resolve_subscription_public_host",
        lambda _: "198.51.100.1",
    )
    monkeypatch.setattr(
        "tulipbridge.wan_dns_check.fetch_public_ipv4",
        lambda: "198.51.100.2",
    )
    lines = build_wan_dns_lines()
    assert any("Mismatch" in L for L in lines)


def test_wan_dns_fqdn_match(isolated_home, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tulipbridge.wan_dns_check.resolve_subscription_public_host",
        lambda _: "vpn.example.com",
    )
    monkeypatch.setattr(
        "tulipbridge.wan_dns_check.fetch_public_ipv4",
        lambda: "203.0.113.5",
    )
    fake = [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            6,
            "",
            ("203.0.113.5", 0),
        ),
    ]
    with patch("tulipbridge.wan_dns_check.socket.getaddrinfo", return_value=fake):
        lines = build_wan_dns_lines()
    assert any("Match" in L and "203.0.113.5" in L for L in lines)


def test_wan_dns_fqdn_mismatch(isolated_home, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tulipbridge.wan_dns_check.resolve_subscription_public_host",
        lambda _: "vpn.example.com",
    )
    monkeypatch.setattr(
        "tulipbridge.wan_dns_check.fetch_public_ipv4",
        lambda: "203.0.113.9",
    )
    fake = [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            6,
            "",
            ("198.51.100.99", 0),
        ),
    ]
    with patch("tulipbridge.wan_dns_check.socket.getaddrinfo", return_value=fake):
        lines = build_wan_dns_lines()
    assert any("Mismatch" in L for L in lines)


def test_wan_dns_resolve_failed(isolated_home, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tulipbridge.wan_dns_check.resolve_subscription_public_host",
        lambda _: "bad.example.invalid",
    )
    monkeypatch.setattr(
        "tulipbridge.wan_dns_check.fetch_public_ipv4",
        lambda: "203.0.113.1",
    )
    with patch(
        "tulipbridge.wan_dns_check.socket.getaddrinfo",
        side_effect=OSError("NXDOMAIN"),
    ):
        lines = build_wan_dns_lines()
    assert any("failed" in L.lower() for L in lines)
