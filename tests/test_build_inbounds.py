"""Acceptance-oriented tests: inbound count vs ServerBuildOptions (no sing-box binary required)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tulipbridge.config import ServerBuildOptions, build_config
from tulipbridge.paths import set_data_root


@pytest.fixture
def isolated_home(tmp_path: Path):
    """Use empty tulipbridge data root; reset override after test."""
    set_data_root(tmp_path)
    yield tmp_path
    set_data_root(None)


def _minimal_reality_keys() -> dict[str, str]:
    return {
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "reality_private_key": "dummy-private",
        "reality_public_key": "dummy-public",
        "short_id": "a1b2c3d4",
    }


def _full_keys(tmp_path: Path) -> dict[str, str]:
    tls = tmp_path / "etc" / "tls"
    tls.mkdir(parents=True)
    (tls / "cert.pem").write_text("-----BEGIN CERTIFICATE-----\nX\n-----END CERTIFICATE-----\n")
    (tls / "key.pem").write_text("-----BEGIN PRIVATE KEY-----\nY\n-----END PRIVATE KEY-----\n")
    k = _minimal_reality_keys()
    k.update(
        {
            "hysteria2_password": "hy2-secret",
            "tuic_password": "tuic-secret",
            "tls_cert_path": "tls/cert.pem",
            "tls_key_path": "tls/key.pem",
        }
    )
    return k


def test_vless_only_one_inbound(isolated_home: Path) -> None:
    keys = _minimal_reality_keys()
    opts = ServerBuildOptions(enable_hysteria2=False, enable_tuic=False, vless_tcp_port=8443)
    cfg = build_config(keys, opts)
    assert len(cfg["inbounds"]) == 1
    assert cfg["inbounds"][0]["type"] == "vless"


def test_three_inbounds_when_all_enabled(isolated_home: Path) -> None:
    keys = _full_keys(isolated_home)
    opts = ServerBuildOptions()
    cfg = build_config(keys, opts)
    types = [i["type"] for i in cfg["inbounds"]]
    assert types == ["vless", "hysteria2", "tuic"]


def test_listen_address_matches_platform(isolated_home: Path) -> None:
    """Windows: avoid [::]+0.0.0.0 dual bind sing-box fatal; POSIX keeps dual-stack ::."""
    keys = _full_keys(isolated_home)
    cfg = build_config(keys, ServerBuildOptions())
    expected = "0.0.0.0" if sys.platform == "win32" else "::"
    assert all(ib["listen"] == expected for ib in cfg["inbounds"])


def test_udp_only_two_inbounds(isolated_home: Path) -> None:
    keys = _full_keys(isolated_home)
    opts = ServerBuildOptions(
        enable_vless=False,
        enable_hysteria2=True,
        enable_tuic=True,
    )
    cfg = build_config(keys, opts)
    types = [i["type"] for i in cfg["inbounds"]]
    assert types == ["hysteria2", "tuic"]
