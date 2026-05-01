"""Regression tests for share URI construction and subscription bundle."""

from __future__ import annotations

import base64
from pathlib import Path

from tulipbridge.config import ServerBuildOptions, parse_server_build_options_from_config
from tulipbridge.share_links import (
    build_hysteria2_uri,
    build_tuic_uri,
    build_vless_reality_uri,
    collect_share_uris,
    export_share_bundle,
    format_uri_host,
    write_subscribe_bundle,
)

_SAMPLE_KEYS = {
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "reality_public_key": "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789abcd",
    "short_id": "0123456789abcdef",
    "hysteria2_password": "hy2:p@ss/word",
    "tuic_password": "tuic secret",
}

_SAMPLE_OPTS = ServerBuildOptions(
    enable_vless=True,
    enable_hysteria2=True,
    enable_tuic=True,
    vless_tcp_port=443,
    hysteria2_udp_port=8444,
    tuic_udp_port=8445,
    reality_sni="www.microsoft.com",
    tls_server_name="tulipbridge.local",
)


def test_format_uri_host_ipv4_and_ipv6() -> None:
    assert format_uri_host(" 198.51.100.1 ") == "198.51.100.1"
    assert format_uri_host("2001:db8::1") == "[2001:db8::1]"
    assert format_uri_host("[2001:db8::1]") == "[2001:db8::1]"


def test_vless_reality_uri_snapshot() -> None:
    uri = build_vless_reality_uri(_SAMPLE_KEYS, _SAMPLE_OPTS, "198.51.100.1")
    assert uri == (
        "vless://550e8400-e29b-41d4-a716-446655440000@198.51.100.1:443?"
        "encryption=none&security=reality&type=tcp&sni=www.microsoft.com&fp=chrome&"
        "pbk=AbCdEfGhIjKlMnOpQrStUvWxYz0123456789abcd&sid=0123456789abcdef&"
        "flow=xtls-rprx-vision#tulipbridge-vless"
    )


def test_hysteria2_uri_encodes_password() -> None:
    uri = build_hysteria2_uri(_SAMPLE_KEYS, _SAMPLE_OPTS, "198.51.100.1")
    assert uri.startswith("hysteria2://")
    assert "hy2%3Ap%40ss%2Fword" in uri
    assert "insecure=1" in uri
    assert "sni=tulipbridge.local" in uri
    assert "@198.51.100.1:8444?" in uri


def test_tuic_uri_encodes_userinfo() -> None:
    uri = build_tuic_uri(_SAMPLE_KEYS, _SAMPLE_OPTS, "198.51.100.1")
    assert uri.startswith("tuic://")
    assert "allow_insecure=1" in uri
    assert "sni=tulipbridge.local" in uri
    assert "@198.51.100.1:8445?" in uri


def test_export_share_bundle_writes_files(tmp_path: Path) -> None:
    out = tmp_path / "sub"
    result = export_share_bundle(
        _SAMPLE_KEYS,
        _SAMPLE_OPTS,
        "198.51.100.1",
        out_dir=out,
        print_qr=False,
        write_png=False,
    )
    assert result["plain_path"] is not None
    assert result["subscription_path"] is not None
    assert result["plain_path"].is_file()
    assert result["subscription_path"].is_file()
    assert len(result["uris"]) == 3


def test_subscription_base64_matches_plain(tmp_path: Path) -> None:
    uris = collect_share_uris(_SAMPLE_KEYS, _SAMPLE_OPTS, "10.0.0.1")
    plain, sub = write_subscribe_bundle(uris, tmp_path)
    body = plain.read_text(encoding="utf-8")
    decoded = base64.standard_b64decode(sub.read_text(encoding="utf-8").strip()).decode("utf-8")
    assert decoded == body


def test_parse_server_build_options_from_config() -> None:
    cfg = {
        "inbounds": [
            {
                "type": "vless",
                "listen_port": 1443,
                "tls": {"server_name": "cdn.example.com"},
            },
            {"type": "hysteria2", "listen_port": 9444, "tls": {"server_name": "hy.example"}},
            {"type": "tuic", "listen_port": 9445, "tls": {"server_name": "hy.example"}},
        ]
    }
    opts = parse_server_build_options_from_config(cfg)
    assert opts.enable_vless and opts.enable_hysteria2 and opts.enable_tuic
    assert opts.vless_tcp_port == 1443
    assert opts.reality_sni == "cdn.example.com"
    assert opts.hysteria2_udp_port == 9444
    assert opts.tuic_udp_port == 9445
    assert opts.tls_server_name == "hy.example"


def test_collect_respects_disabled_protocols() -> None:
    opts = ServerBuildOptions(
        enable_vless=True,
        enable_hysteria2=False,
        enable_tuic=False,
        vless_tcp_port=443,
    )
    pairs = collect_share_uris(_SAMPLE_KEYS, opts, "1.1.1.1")
    assert len(pairs) == 1
    assert pairs[0][0] == "vless-reality"
