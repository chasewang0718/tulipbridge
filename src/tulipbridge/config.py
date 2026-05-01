"""Build sing-box JSON config for VLESS-Reality and optional Hysteria2 / TUIC inbounds."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tulipbridge.paths import config_json_path, etc_dir, singbox_log_path


@dataclass(frozen=True)
class ServerBuildOptions:
    """Controls which inbounds are rendered into config.json."""

    enable_vless: bool = True
    enable_hysteria2: bool = True
    enable_tuic: bool = True
    vless_tcp_port: int = 443
    hysteria2_udp_port: int = 8444
    tuic_udp_port: int = 8445
    reality_sni: str = "www.microsoft.com"
    """SNI / handshake target for VLESS Reality."""

    tls_server_name: str = "tulipbridge.local"
    """TLS server_name on Hy2/TUIC inbounds (must match self-signed cert CN)."""


class ConfigError(ValueError):
    """Invalid port combination or missing keys for enabled protocols."""


def validate_listen_ports(opts: ServerBuildOptions) -> None:
    """Reject duplicate TCP listen ports or duplicate UDP listen ports among enabled inbounds."""
    tcp: list[tuple[str, int]] = []
    udp: list[tuple[str, int]] = []
    if opts.enable_vless:
        tcp.append(("vless-reality", opts.vless_tcp_port))
    if opts.enable_hysteria2:
        udp.append(("hysteria2", opts.hysteria2_udp_port))
    if opts.enable_tuic:
        udp.append(("tuic", opts.tuic_udp_port))

    def _dup(items: list[tuple[str, int]], label: str) -> None:
        seen: dict[int, str] = {}
        for tag, p in items:
            if p in seen:
                raise ConfigError(
                    f"Duplicate {label} port {p}: both '{seen[p]}' and '{tag}'."
                )
            seen[p] = tag

    _dup(tcp, "TCP")
    _dup(udp, "UDP")


def _tls_paths(keys: dict[str, Any]) -> tuple[Path, Path]:
    rel_cert = str(keys.get("tls_cert_path", "tls/cert.pem")).strip()
    rel_key = str(keys.get("tls_key_path", "tls/key.pem")).strip()
    return etc_dir() / rel_cert, etc_dir() / rel_key


def build_config(keys: dict[str, Any], opts: ServerBuildOptions) -> dict[str, Any]:
    """Return sing-box server configuration dict."""
    validate_listen_ports(opts)

    if opts.enable_hysteria2 or opts.enable_tuic:
        for field in ("tls_cert_path", "tls_key_path"):
            if field not in keys or not str(keys.get(field, "")).strip():
                raise ConfigError(f"Missing keys.json field '{field}' for QUIC inbounds.")
        cpath, kpath = _tls_paths(keys)
        if not cpath.is_file() or not kpath.is_file():
            raise ConfigError(f"TLS PEM files not found: {cpath} / {kpath}")

    if opts.enable_hysteria2 and not str(keys.get("hysteria2_password", "")).strip():
        raise ConfigError("Missing hysteria2_password in keys.json.")
    if opts.enable_tuic and not str(keys.get("tuic_password", "")).strip():
        raise ConfigError("Missing tuic_password in keys.json.")

    uid = str(keys["uuid"]).strip()
    priv = str(keys["reality_private_key"]).strip()
    short_id = str(keys["short_id"]).strip()
    sni = opts.reality_sni.strip()
    tls_name = opts.tls_server_name.strip()

    log_file = singbox_log_path()
    inbounds: list[dict[str, Any]] = []

    if opts.enable_vless:
        inbounds.append(
            {
                "type": "vless",
                "tag": "vless-reality",
                "listen": "::",
                "listen_port": opts.vless_tcp_port,
                "users": [
                    {
                        "uuid": uid,
                        "flow": "xtls-rprx-vision",
                    }
                ],
                "tls": {
                    "enabled": True,
                    "server_name": sni,
                    "reality": {
                        "enabled": True,
                        "handshake": {"server": sni, "server_port": 443},
                        "private_key": priv,
                        "short_id": [short_id],
                    },
                },
            }
        )

    cert_path, key_path = _tls_paths(keys)

    if opts.enable_hysteria2:
        inbounds.append(
            {
                "type": "hysteria2",
                "tag": "hysteria2-in",
                "listen": "::",
                "listen_port": opts.hysteria2_udp_port,
                "users": [
                    {
                        "password": str(keys["hysteria2_password"]).strip(),
                    }
                ],
                "tls": {
                    "enabled": True,
                    "server_name": tls_name,
                    "certificate_path": str(cert_path.resolve()),
                    "key_path": str(key_path.resolve()),
                },
            }
        )

    if opts.enable_tuic:
        inbounds.append(
            {
                "type": "tuic",
                "tag": "tuic-in",
                "listen": "::",
                "listen_port": opts.tuic_udp_port,
                "users": [
                    {
                        "uuid": uid,
                        "password": str(keys["tuic_password"]).strip(),
                    }
                ],
                "tls": {
                    "enabled": True,
                    "server_name": tls_name,
                    "certificate_path": str(cert_path.resolve()),
                    "key_path": str(key_path.resolve()),
                },
            }
        )

    if not inbounds:
        raise ConfigError("At least one inbound protocol must be enabled.")

    return {
        "log": {
            "level": "info",
            "output": str(log_file),
            "timestamp": True,
        },
        "inbounds": inbounds,
        "outbounds": [
            {"type": "direct", "tag": "direct"},
            {"type": "block", "tag": "block"},
        ],
    }


def write_config(config: dict[str, Any]) -> Path:
    """Write config.json under the active etc directory."""
    path = config_json_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return path


def parse_server_build_options_from_config(cfg: dict[str, Any]) -> ServerBuildOptions:
    """Rebuild :class:`ServerBuildOptions` from a saved sing-box ``config.json`` dict."""
    enable_vless = False
    enable_hysteria2 = False
    enable_tuic = False
    vless_tcp_port = 443
    hysteria2_udp_port = 8444
    tuic_udp_port = 8445
    reality_sni = "www.microsoft.com"
    tls_server_name = "tulipbridge.local"

    for ib in cfg.get("inbounds") or []:
        if not isinstance(ib, dict):
            continue
        itype = ib.get("type")
        port = int(ib.get("listen_port") or 443)
        tls = ib.get("tls") if isinstance(ib.get("tls"), dict) else {}

        if itype == "vless":
            enable_vless = True
            vless_tcp_port = port
            reality_sni = str(tls.get("server_name") or reality_sni).strip() or reality_sni
        elif itype == "hysteria2":
            enable_hysteria2 = True
            hysteria2_udp_port = port
            sn = str(tls.get("server_name") or tls_server_name).strip()
            tls_server_name = sn or tls_server_name
        elif itype == "tuic":
            enable_tuic = True
            tuic_udp_port = port
            sn = str(tls.get("server_name") or tls_server_name).strip()
            tls_server_name = sn or tls_server_name

    return ServerBuildOptions(
        enable_vless=enable_vless,
        enable_hysteria2=enable_hysteria2,
        enable_tuic=enable_tuic,
        vless_tcp_port=vless_tcp_port,
        hysteria2_udp_port=hysteria2_udp_port,
        tuic_udp_port=tuic_udp_port,
        reality_sni=reality_sni,
        tls_server_name=tls_server_name,
    )
