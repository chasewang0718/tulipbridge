"""Human-readable lines for ``tulipbridge status`` (Phase 5 thin slice)."""

from __future__ import annotations

import json
import socket

from tulipbridge.clash_memory import clash_memory_status_lines
from tulipbridge.config import parse_server_build_options_from_config
from tulipbridge.paths import config_json_path, get_tulipbridge_home, pid_file_path
from tulipbridge.process import is_running, read_pid
from tulipbridge.wan_dns_check import build_wan_dns_lines


def probe_tcp_local(port: int, *, timeout: float = 1.0) -> str:
    """Probe localhost TCP ``port``; return a short status tag."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            pass
        return "listen_ok"
    except ConnectionRefusedError:
        return "nothing_listening"
    except OSError as e:
        return f"check_failed ({e})"


def build_status_lines() -> list[str]:
    """Return lines to print for ``status`` (no trailing newlines in each string)."""
    lines: list[str] = []
    root = get_tulipbridge_home()
    lines.append(f"Data directory: {root.resolve()}")

    pf = pid_file_path()
    if not pf.is_file():
        lines.append("sing-box process: stopped (no PID file)")
    elif is_running():
        pid = read_pid()
        lines.append(f"sing-box process: running (PID {pid})")
    else:
        raw = read_pid()
        lines.append(
            "sing-box process: stale PID file "
            f"(recorded PID {raw}, process not running)"
        )
        lines.append("  Hint: remove the PID file or run `tulipbridge init --force`.")

    cfg_path = config_json_path()
    lines.append("")
    if not cfg_path.is_file():
        lines.append(f"No config ({cfg_path}). Run `tulipbridge init` first.")
        lines.extend(build_wan_dns_lines())
        return lines

    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        opts = parse_server_build_options_from_config(cfg)
    except (json.JSONDecodeError, OSError, TypeError) as e:
        lines.append(f"Could not read config: {e}")
        lines.extend(build_wan_dns_lines())
        return lines

    lines.append("Inbounds (from config.json):")
    any_inbound = False
    if opts.enable_vless:
        lines.append(f"  VLESS-Reality (TCP): {opts.vless_tcp_port}")
        any_inbound = True
    if opts.enable_hysteria2:
        lines.append(f"  Hysteria 2 (UDP):    {opts.hysteria2_udp_port}")
        any_inbound = True
    if opts.enable_tuic:
        lines.append(f"  TUIC (UDP):          {opts.tuic_udp_port}")
        any_inbound = True
    if not any_inbound:
        lines.append("  (none enabled)")

    lines.append("")
    lines.append("Local probes (this machine only):")

    if opts.enable_vless:
        tag = probe_tcp_local(opts.vless_tcp_port)
        lines.append(f"  TCP {opts.vless_tcp_port} (VLESS): {tag}")
    else:
        lines.append("  TCP (VLESS): not configured")

    lines.append("")
    lines.append(
        "UDP ports cannot be verified with a plain TCP connect; "
        "use sing-box logs or an external UDP test."
    )
    if opts.enable_hysteria2:
        lines.append(
            f"  UDP {opts.hysteria2_udp_port} (Hysteria 2): configured (not probed)"
        )
    if opts.enable_tuic:
        lines.append(f"  UDP {opts.tuic_udp_port} (TUIC): configured (not probed)")
    if not opts.enable_hysteria2 and not opts.enable_tuic:
        lines.append("  (no UDP inbounds)")

    lines.extend(clash_memory_status_lines(cfg))

    lines.extend(build_wan_dns_lines())
    return lines
