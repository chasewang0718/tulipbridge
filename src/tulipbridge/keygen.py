"""Generate and persist TLS/Reality credentials for sing-box."""

from __future__ import annotations

import json
import re
import secrets
import subprocess
import uuid
from pathlib import Path
from typing import Any

from tulipbridge.paths import etc_dir, keys_json_path, set_keys_json_permissions, tls_dir
from tulipbridge.tls_local import TLSGenerationError, ensure_tls_cert_pair


class KeyGenerationError(RuntimeError):
    """Failed to generate or parse sing-box keys."""


_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

_TLS_REL_CERT = "tls/cert.pem"
_TLS_REL_KEY = "tls/key.pem"


def _parse_reality_keypair(stdout: str) -> tuple[str, str]:
    priv: str | None = None
    pub: str | None = None
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("PrivateKey:"):
            priv = line.split(":", 1)[1].strip()
        elif line.startswith("PublicKey:"):
            pub = line.split(":", 1)[1].strip()
    if not priv or not pub:
        raise KeyGenerationError(
            "Could not parse sing-box reality-keypair output (expected PrivateKey/PublicKey lines)."
        )
    return priv, pub


def generate_keys(singbox_bin: Path) -> dict[str, Any]:
    """Generate UUID, Reality keypair via sing-box, and short_id."""
    if not singbox_bin.is_file():
        raise KeyGenerationError(f"sing-box not found at {singbox_bin}")

    uid = str(uuid.uuid4())

    proc = subprocess.run(
        [str(singbox_bin), "generate", "reality-keypair"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise KeyGenerationError(
            f"sing-box generate reality-keypair failed ({proc.returncode}): {err}"
        )

    priv, pub = _parse_reality_keypair(proc.stdout or "")
    short_id = secrets.token_hex(4)

    keys = {
        "uuid": uid,
        "reality_private_key": priv,
        "reality_public_key": pub,
        "short_id": short_id,
    }
    save_keys(keys)
    return keys


def save_keys(keys: dict[str, Any]) -> None:
    path = keys_json_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(keys, indent=2) + "\n", encoding="utf-8")
    set_keys_json_permissions(path)


def load_keys() -> dict[str, Any] | None:
    path = keys_json_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _validate_reality_keys(keys: dict[str, Any]) -> bool:
    required = ("uuid", "reality_private_key", "reality_public_key", "short_id")
    for k in required:
        if k not in keys or not isinstance(keys[k], str) or not keys[k].strip():
            return False
    if not _UUID_RE.match(keys["uuid"].strip()):
        return False
    return True


def _ensure_udp_secrets(
    keys: dict[str, Any],
    singbox_bin: Path,
    tls_server_name: str,
    *,
    need_hysteria2: bool,
    need_tuic: bool,
) -> None:
    """Add Hy2/TUIC passwords and TLS PEMs under etc/tls/. Mutates keys and saves."""
    if not need_hysteria2 and not need_tuic:
        return

    tls_dir().mkdir(parents=True, exist_ok=True)
    cert_path = etc_dir() / _TLS_REL_CERT
    key_path = etc_dir() / _TLS_REL_KEY

    try:
        ensure_tls_cert_pair(
            singbox_bin,
            tls_server_name,
            cert_path=cert_path,
            key_path=key_path,
        )
    except TLSGenerationError as e:
        raise KeyGenerationError(str(e)) from e

    keys["tls_cert_path"] = _TLS_REL_CERT
    keys["tls_key_path"] = _TLS_REL_KEY
    keys["tls_server_name"] = tls_server_name

    if need_hysteria2 and (
        "hysteria2_password" not in keys
        or not str(keys.get("hysteria2_password", "")).strip()
    ):
        keys["hysteria2_password"] = secrets.token_urlsafe(32)

    if need_tuic and (
        "tuic_password" not in keys or not str(keys.get("tuic_password", "")).strip()
    ):
        keys["tuic_password"] = secrets.token_urlsafe(32)

    save_keys(keys)


def ensure_keys(
    singbox_bin: Path,
    *,
    enable_vless: bool = True,
    enable_hysteria2: bool = True,
    enable_tuic: bool = True,
    tls_server_name: str = "tulipbridge.local",
) -> dict[str, Any]:
    """
    Load keys.json if Reality fields are valid; otherwise generate.

    When Hy2 or TUIC is enabled, ensure TLS cert pair and UDP passwords exist (migration-safe).
    """
    existing = load_keys()
    if existing and _validate_reality_keys(existing):
        keys = existing
    else:
        keys = generate_keys(singbox_bin)

    need_tls = enable_hysteria2 or enable_tuic
    if need_tls:
        _ensure_udp_secrets(
            keys,
            singbox_bin,
            tls_server_name.strip() or "tulipbridge.local",
            need_hysteria2=enable_hysteria2,
            need_tuic=enable_tuic,
        )

    return keys
