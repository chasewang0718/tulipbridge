"""Tests for sing-box config port validation."""

from __future__ import annotations

import pytest

from tulipbridge.config import ConfigError, ServerBuildOptions, validate_listen_ports


def test_tcp_duplicate_raises() -> None:
    opts = ServerBuildOptions(
        enable_vless=True,
        enable_hysteria2=False,
        enable_tuic=False,
        vless_tcp_port=443,
    )
    validate_listen_ports(opts)

    # Two TCP ports cannot be enabled with same number — only one TCP inbound in Phase 2.
    # Simulate duplicate by enabling same port twice is impossible with current schema;
    # instead duplicate UDP:
    opts2 = ServerBuildOptions(
        enable_hysteria2=True,
        enable_tuic=True,
        hysteria2_udp_port=8444,
        tuic_udp_port=8444,
    )
    with pytest.raises(ConfigError, match="Duplicate UDP"):
        validate_listen_ports(opts2)


def test_tcp443_udp443_coexist() -> None:
    """TCP and UDP port numbers are independent namespaces."""
    opts = ServerBuildOptions(
        enable_vless=True,
        enable_hysteria2=True,
        enable_tuic=False,
        vless_tcp_port=443,
        hysteria2_udp_port=443,
    )
    validate_listen_ports(opts)
