"""Build client share URIs, subscription bundle, and QR outputs for Phase 3."""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

import segno

from tulipbridge.config import ServerBuildOptions
from tulipbridge.paths import subscribe_dir


def format_uri_host(public_host: str) -> str:
    """Bracket IPv6 literals for URI authority; leave hostnames and bracketed IPv6 unchanged."""
    host = public_host.strip()
    if host.startswith("[") and host.endswith("]"):
        return host
    if ":" in host:
        return f"[{host}]"
    return host


def build_vless_reality_uri(
    keys: dict[str, Any],
    opts: ServerBuildOptions,
    public_host: str,
) -> str:
    """Shadowrocket / sing-box compatible VLESS Reality URI."""
    uid = str(keys["uuid"]).strip()
    pk = str(keys["reality_public_key"]).strip()
    sid = str(keys["short_id"]).strip()
    sni = opts.reality_sni.strip()
    port = opts.vless_tcp_port
    host = format_uri_host(public_host)

    q = {
        "encryption": "none",
        "security": "reality",
        "type": "tcp",
        "sni": sni,
        "fp": "chrome",
        "pbk": pk,
        "sid": sid,
        "flow": "xtls-rprx-vision",
    }
    query = urlencode(q)
    return f"vless://{uid}@{host}:{port}?{query}#tulipbridge-vless"


def build_hysteria2_uri(
    keys: dict[str, Any],
    opts: ServerBuildOptions,
    public_host: str,
) -> str:
    """Hysteria 2 URI with self-signed TLS (insecure + sni)."""
    pwd = str(keys["hysteria2_password"]).strip()
    port = opts.hysteria2_udp_port
    host = format_uri_host(public_host)
    sni = opts.tls_server_name.strip()
    auth = quote(pwd, safe="")
    q = urlencode({"insecure": "1", "sni": sni})
    return f"hysteria2://{auth}@{host}:{port}?{q}#tulipbridge-hy2"


def build_tuic_uri(
    keys: dict[str, Any],
    opts: ServerBuildOptions,
    public_host: str,
) -> str:
    """TUIC v5 URI (UDP); allow_insecure for self-signed."""
    uid = str(keys["uuid"]).strip()
    pwd = str(keys["tuic_password"]).strip()
    port = opts.tuic_udp_port
    host = format_uri_host(public_host)
    sni = opts.tls_server_name.strip()
    userinfo = f"{quote(uid, safe='')}:{quote(pwd, safe='')}"
    q = urlencode(
        {
            "congestion_control": "cubic",
            "udp_relay_mode": "native",
            "sni": sni,
            "allow_insecure": "1",
            "alpn": "h3",
        }
    )
    return f"tuic://{userinfo}@{host}:{port}?{q}#tulipbridge-tuic"


def collect_share_uris(
    keys: dict[str, Any],
    opts: ServerBuildOptions,
    public_host: str,
) -> list[tuple[str, str]]:
    """Return list of (label, uri) for enabled protocols."""
    out: list[tuple[str, str]] = []
    if opts.enable_vless:
        out.append(("vless-reality", build_vless_reality_uri(keys, opts, public_host)))
    if opts.enable_hysteria2:
        out.append(("hysteria2", build_hysteria2_uri(keys, opts, public_host)))
    if opts.enable_tuic:
        out.append(("tuic", build_tuic_uri(keys, opts, public_host)))
    return out


def write_subscribe_bundle(
    uris: list[tuple[str, str]],
    out_dir: Path,
) -> tuple[Path, Path]:
    """
    Write ``uris-plain.txt`` (one URI per line) and ``subscription.txt`` (Base64 of UTF-8 plain).

    Returns paths to plain and subscription files.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    plain_lines = [uri for _label, uri in uris]
    plain_body = "\n".join(plain_lines) + ("\n" if plain_lines else "")
    plain_path = out_dir / "uris-plain.txt"
    plain_path.write_text(plain_body, encoding="utf-8")

    sub_path = out_dir / "subscription.txt"
    b64 = base64.standard_b64encode(plain_body.encode("utf-8")).decode("ascii")
    sub_path.write_text(b64 + "\n", encoding="utf-8")
    return plain_path, sub_path


def write_qr_pngs(uris: list[tuple[str, str]], out_dir: Path) -> list[Path]:
    """Write one PNG QR per URI; returns paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for label, uri in uris:
        qr = segno.make(uri, error="m")
        fname = f"qr-{label}.png"
        path = out_dir / fname
        qr.save(path, scale=8, dark="black", light="white")
        paths.append(path)
    return paths


def print_qr_terminal(uris: list[tuple[str, str]]) -> None:
    """Print compact ASCII QR codes to stdout (one block per URI)."""
    for label, uri in uris:
        print()
        print(f"--- QR: {label} ---")
        qr = segno.make(uri, error="m")
        buf = io.StringIO()
        qr.terminal(out=buf, border=1)
        print(buf.getvalue(), end="")


def export_share_bundle(
    keys: dict[str, Any],
    opts: ServerBuildOptions,
    public_host: str,
    *,
    out_dir: Path | None = None,
    print_qr: bool = True,
    write_png: bool = True,
) -> dict[str, Any]:
    """
    Build URIs, write plain + Base64 subscription, optional PNG + terminal QR.

    Returns dict with paths and uri list.
    """
    base = out_dir or subscribe_dir()
    uris = collect_share_uris(keys, opts, public_host)
    if not uris:
        return {"uris": [], "plain_path": None, "subscription_path": None, "png_paths": []}

    plain_path, sub_path = write_subscribe_bundle(uris, base)
    png_paths: list[Path] = []
    if write_png:
        png_paths = write_qr_pngs(uris, base)

    if print_qr:
        print_qr_terminal(uris)

    return {
        "uris": uris,
        "plain_path": plain_path,
        "subscription_path": sub_path,
        "png_paths": png_paths,
    }
