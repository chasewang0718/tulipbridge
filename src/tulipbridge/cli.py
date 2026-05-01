"""CLI entrypoint for tulipbridge."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from tulipbridge import __version__
from tulipbridge.binary import BinaryDownloadError, ensure_singbox, singbox_version
from tulipbridge.config import (
    ConfigError,
    ServerBuildOptions,
    build_config,
    parse_server_build_options_from_config,
    write_config,
)
from tulipbridge.keygen import KeyGenerationError, ensure_keys, load_keys
from tulipbridge.paths import (
    config_json_path,
    ensure_dirs,
    get_tulipbridge_home,
    portable_data_path,
    set_data_root,
    subscribe_dir,
)
from tulipbridge.process import is_running, start_singbox, stop_singbox
from tulipbridge.share_links import export_share_bundle


def _print_share_export_summary(result: dict) -> None:
    """Pretty-print URIs and paths after :func:`export_share_bundle`."""
    uris = result.get("uris") or []
    for label, uri in uris:
        print(f"  [{label}]")
        print(f"    {uri}")
    pp = result.get("plain_path")
    sp = result.get("subscription_path")
    if pp:
        print(f"  Plain URIs file:      {pp}")
    if sp:
        print(f"  Base64 subscription: {sp}")
    for p in result.get("png_paths") or []:
        print(f"  QR PNG:               {p}")


def _validate_singbox_config(singbox_exe: str, config_path: str) -> None:
    proc = subprocess.run(
        [singbox_exe, "check", "-c", config_path],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"sing-box rejected config: {err}")


def _cmd_init(args: argparse.Namespace) -> int:
    if not args.enable_vless and not args.enable_hysteria2 and not args.enable_tuic:
        print(
            "Error: enable at least one protocol (--vless / --hysteria2 / --tuic).",
            file=sys.stderr,
        )
        return 1

    opts = ServerBuildOptions(
        enable_vless=args.enable_vless,
        enable_hysteria2=args.enable_hysteria2,
        enable_tuic=args.enable_tuic,
        vless_tcp_port=int(args.port),
        hysteria2_udp_port=int(args.hy2_port),
        tuic_udp_port=int(args.tuic_port),
        reality_sni=str(args.sni).strip(),
        tls_server_name=str(args.tls_sni).strip() or "tulipbridge.local",
    )

    root = get_tulipbridge_home()
    print(f"[1/7] Creating data directories under {root} ...")
    ensure_dirs()

    print("[2/7] Ensuring sing-box binary...")
    try:
        sb_path = ensure_singbox(version=args.singbox_version)
    except BinaryDownloadError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    ver = singbox_version() or "?"
    print(f"      sing-box at {sb_path} (version {ver})")

    print("[3/7] Loading or generating keys (Reality + optional QUIC TLS)...")
    try:
        keys = ensure_keys(
            sb_path,
            enable_vless=opts.enable_vless,
            enable_hysteria2=opts.enable_hysteria2,
            enable_tuic=opts.enable_tuic,
            tls_server_name=opts.tls_server_name,
        )
    except KeyGenerationError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print("[4/7] Writing config.json...")
    try:
        cfg = build_config(keys, opts)
    except ConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    try:
        cfg_path = write_config(cfg)
    except OSError as e:
        print(f"Error: could not write config: {e}", file=sys.stderr)
        return 1

    print("[5/7] Validating config...")
    try:
        _validate_singbox_config(str(sb_path), str(cfg_path))
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except subprocess.TimeoutExpired:
        print("Error: sing-box check timed out.", file=sys.stderr)
        return 1

    if is_running():
        if args.force:
            print("      Stopping existing sing-box (--force)...")
            stop_singbox()
        else:
            print(
                "Error: sing-box already appears to be running. Stop it first or use --force.",
                file=sys.stderr,
            )
            return 1

    print("[6/7] Starting sing-box...")
    try:
        pid = start_singbox(cfg_path)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print("[7/7] Done.")
    public_host = str(args.public_host).strip() if args.public_host else ""

    pub = keys.get("reality_public_key", "")
    print()
    print("TulipBridge init complete.")
    print(f"  Process PID:          {pid}")
    print(f"  Data directory:       {root}")
    print(f"  Config:               {cfg_path}")
    print()
    print("  Protocols:")
    if opts.enable_vless:
        print(f"    VLESS + Reality    TCP  {opts.vless_tcp_port}")
    if opts.enable_hysteria2:
        print(f"    Hysteria 2          UDP  {opts.hysteria2_udp_port}")
    if opts.enable_tuic:
        print(f"    TUIC v5             UDP  {opts.tuic_udp_port}")
    print()
    if opts.enable_vless:
        print(f"  VLESS UUID:             {keys.get('uuid')}")
        print(f"  Reality public key:     {pub}")
        print(f"  Reality short_id:       {keys.get('short_id')}")
        print(f"  Reality SNI:            {opts.reality_sni}")
    if opts.enable_hysteria2:
        print(f"  Hy2 password:           {keys.get('hysteria2_password')}")
    if opts.enable_tuic:
        print(f"  TUIC password:          {keys.get('tuic_password')}")
        if opts.enable_vless:
            print("  TUIC UUID:              (same as VLESS UUID)")
        else:
            print(f"  TUIC UUID:              {keys.get('uuid')}")
    if opts.enable_hysteria2 or opts.enable_tuic:
        print(f"  QUIC TLS server_name:   {opts.tls_server_name}")
        print(f"  TLS cert (Hy2/TUIC):    {etc_tls_hint(keys)}")
    print()
    print("Router port forwarding:")
    if opts.enable_vless:
        print(f"  Forward WAN TCP {opts.vless_tcp_port} -> this host TCP {opts.vless_tcp_port}")
    if opts.enable_hysteria2:
        hp = opts.hysteria2_udp_port
        print(f"  Forward WAN UDP {hp} -> this host UDP {hp}")
    if opts.enable_tuic:
        tp = opts.tuic_udp_port
        print(f"  Forward WAN UDP {tp} -> this host UDP {tp}")
    print()
    print(
        "Clients using Hy2/TUIC with this self-signed TLS cert must allow insecure "
        "or pin the cert; share links include insecure/SNI fields matching this setup."
    )

    if public_host:
        print()
        print("Subscription files & QR codes (public host)...")
        result = export_share_bundle(
            keys,
            opts,
            public_host,
            out_dir=subscribe_dir(),
            print_qr=True,
            write_png=True,
        )
        _print_share_export_summary(result)
    else:
        print()
        print(
            "Tip: pass --public-host YOUR_WAN_IP_OR_DOMAIN on init to write subscribe/ "
            "and print QR codes. Or run: tulipbridge links --public-host YOUR_WAN_IP_OR_DOMAIN"
        )
        print(f"  Subscribe directory: {subscribe_dir()}")
    return 0


def etc_tls_hint(keys: dict) -> str:
    from tulipbridge.paths import etc_dir

    rel = str(keys.get("tls_cert_path", "tls/cert.pem"))
    return str((etc_dir() / rel).resolve())


def _cmd_links(args: argparse.Namespace) -> int:
    keys = load_keys()
    if not keys:
        print("Error: keys.json not found — run `tulipbridge init` first.", file=sys.stderr)
        return 1
    cfg_path = config_json_path()
    if not cfg_path.is_file():
        print(f"Error: missing {cfg_path}", file=sys.stderr)
        return 1
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"Error: invalid config JSON: {e}", file=sys.stderr)
        return 1
    opts = parse_server_build_options_from_config(cfg)
    if not opts.enable_vless and not opts.enable_hysteria2 and not opts.enable_tuic:
        print("Error: no enabled inbounds in config.json.", file=sys.stderr)
        return 1

    out_dir = args.output_dir if args.output_dir is not None else subscribe_dir()
    host = str(args.public_host).strip()
    print(f"Writing subscription under {out_dir.resolve()} ...")
    result = export_share_bundle(
        keys,
        opts,
        host,
        out_dir=out_dir,
        print_qr=True,
        write_png=True,
    )
    _print_share_export_summary(result)
    return 0


def _cmd_update(_args: argparse.Namespace) -> int:
    print("update: not implemented yet — DDNS / subscription refresh.")
    return 0


def _cmd_status(_args: argparse.Namespace) -> int:
    print("status: not implemented yet — sing-box health & ports.")
    return 0


def _apply_data_root(ns: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """Resolve --data-dir / --portable before any command touches paths."""
    dd = ns.data_dir
    portable = ns.portable
    if dd is not None and portable:
        parser.error("Use either --data-dir or --portable, not both.")
    if dd is not None:
        set_data_root(Path(dd))
    elif portable:
        set_data_root(portable_data_path())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tulipbridge",
        description="Deploy and manage sing-box for TulipBridge home proxy.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Store sing-box, config, and logs under PATH instead of ~/.tulipbridge. "
            "Overrides TULIPBRIDGE_HOME for this run."
        ),
    )
    parser.add_argument(
        "--portable",
        action="store_true",
        help=(
            "Portable mode: use ./tulipbridge-data under the current working directory "
            "(good for USB / self-contained folders). Overrides TULIPBRIDGE_HOME."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="First-time setup: sing-box, keys, config, QR/subscribe.")
    p_init.add_argument(
        "--port",
        type=int,
        default=443,
        help="TCP listen port for VLESS-Reality (default: 443).",
    )
    p_init.add_argument(
        "--hy2-port",
        type=int,
        default=8444,
        metavar="PORT",
        help="UDP listen port for Hysteria 2 (default: 8444). Ignored if Hy2 disabled.",
    )
    p_init.add_argument(
        "--tuic-port",
        type=int,
        default=8445,
        metavar="PORT",
        help="UDP listen port for TUIC (default: 8445). Ignored if TUIC disabled.",
    )
    p_init.add_argument(
        "--sni",
        default="www.microsoft.com",
        help="TLS server_name / Reality handshake target (default: www.microsoft.com).",
    )
    p_init.add_argument(
        "--tls-sni",
        default="tulipbridge.local",
        metavar="NAME",
        help=(
            "TLS server_name for Hy2/TUIC inbounds; must match self-signed cert "
            "(default: tulipbridge.local)."
        ),
    )
    p_init.add_argument(
        "--vless",
        dest="enable_vless",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable VLESS-Reality inbound (default: on).",
    )
    p_init.add_argument(
        "--hysteria2",
        dest="enable_hysteria2",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable Hysteria 2 UDP inbound (default: on).",
    )
    p_init.add_argument(
        "--tuic",
        dest="enable_tuic",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable TUIC v5 UDP inbound (default: on).",
    )
    p_init.add_argument(
        "--singbox-version",
        default=None,
        metavar="TAG",
        help="Install this sing-box release tag (e.g. 1.12.25) instead of latest.",
    )
    p_init.add_argument(
        "--force",
        action="store_true",
        help="If sing-box is already running, stop it and start again.",
    )
    p_init.add_argument(
        "--public-host",
        default=None,
        metavar="HOST",
        help=(
            "Public WAN hostname or IP for share links and subscribe/*. "
            "If omitted, init skips subscription files and QR; run `tulipbridge links` later."
        ),
    )
    p_init.set_defaults(func=_cmd_init)

    p_links = sub.add_parser(
        "links",
        help="Regenerate share URIs, subscribe/subscription.txt, and QR from keys + config.",
    )
    p_links.add_argument(
        "--public-host",
        required=True,
        metavar="HOST",
        help="Public WAN hostname or IP embedded in client URIs.",
    )
    p_links.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help=f"Where to write subscribe files (default: {subscribe_dir()}).",
    )
    p_links.set_defaults(func=_cmd_links)

    p_up = sub.add_parser("update", help="Refresh DDNS / links after IP or cert changes.")
    p_up.set_defaults(func=_cmd_update)

    p_st = sub.add_parser("status", help="Show sing-box and port health.")
    p_st.set_defaults(func=_cmd_status)

    ns = parser.parse_args(argv)
    _apply_data_root(ns, parser)
    return int(ns.func(ns))


if __name__ == "__main__":
    sys.exit(main())
