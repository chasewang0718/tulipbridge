"""Resolve and persist the WAN hostname/IP used in share URIs (Phase 4)."""

from __future__ import annotations

import os
from pathlib import Path

from tulipbridge.paths import etc_dir

_PUBLIC_HOST_FILENAME = "public_host.txt"


def public_host_txt_path() -> Path:
    return etc_dir() / _PUBLIC_HOST_FILENAME


def read_stored_public_host() -> str | None:
    path = public_host_txt_path()
    if not path.is_file():
        return None
    try:
        s = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return s if s else None


def write_stored_public_host(host: str) -> None:
    """Remember last host used for subscribe URIs (DDNS name or IP)."""
    path = public_host_txt_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(host.strip() + "\n", encoding="utf-8")


def resolve_subscription_public_host(cli_public_host: str | None) -> str | None:
    """Host for vless/hy2/tuic URIs: CLI > etc/public_host.txt > CLOUDFLARE_RECORD_NAME."""
    if cli_public_host is not None:
        h = str(cli_public_host).strip()
        if h:
            return h
    stored = read_stored_public_host()
    if stored:
        return stored
    env = os.environ.get("CLOUDFLARE_RECORD_NAME", "").strip()
    if env:
        return env
    return None


def subscription_refresh_hint_lines() -> list[str]:
    """Footer lines for `update`: shorter command when a default host is available."""
    if resolve_subscription_public_host(None):
        return [
            "Refresh subscription files after host/IP changes:",
            "  tulipbridge links",
        ]
    return [
        "Refresh subscription files after host/IP changes:",
        "  tulipbridge links --public-host YOUR_HOST",
    ]
