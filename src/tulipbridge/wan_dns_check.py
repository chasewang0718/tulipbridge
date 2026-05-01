"""Compare outbound IPv4 with DNS A records for the subscription host (Phase 5)."""

from __future__ import annotations

import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout

from tulipbridge.network_public import fetch_public_ipv4
from tulipbridge.public_host import resolve_subscription_public_host

_DNS_TIMEOUT_SEC = 5.0


def _ipv4_a_records(hostname: str) -> tuple[set[str] | None, str | None]:
    """Resolve IPv4 A records via getaddrinfo; None set + message on failure or timeout."""

    def _lookup() -> set[str]:
        infos = socket.getaddrinfo(
            hostname,
            None,
            socket.AF_INET,
            socket.SOCK_STREAM,
        )
        return {item[4][0] for item in infos}

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_lookup)
            return fut.result(timeout=_DNS_TIMEOUT_SEC), None
    except FuturesTimeout:
        return None, "DNS lookup timed out"
    except OSError as e:
        return None, str(e)


def build_wan_dns_lines() -> list[str]:
    """
    Human-readable lines: subscription host vs outbound IPv4 (HTTPS reflectors).

    Uses the same host resolution as ``tulipbridge links`` without ``--public-host``.
    """
    lines: list[str] = []
    lines.append("")
    lines.append("WAN / DNS vs subscription host:")

    host = resolve_subscription_public_host(None)
    if not host:
        lines.append(
            "  (none — set etc/public_host.txt or CLOUDFLARE_RECORD_NAME to enable)"
        )
        return lines

    pub = fetch_public_ipv4()

    try:
        parsed = ipaddress.ip_address(host)
    except ValueError:
        parsed = None

    if parsed is not None:
        if isinstance(parsed, ipaddress.IPv6Address):
            lines.append(
                "  Subscription host is an IPv6 literal; this check compares IPv4 only (skipped)."
            )
            return lines
        lit = str(parsed)
        if not pub:
            lines.append(f"  Literal host: {lit}")
            lines.append("  Outbound IPv4: (could not detect)")
            return lines
        if lit == pub:
            lines.append(f"  Match: literal host {lit} equals outbound IPv4.")
        else:
            lines.append(
                f"  Mismatch: literal host {lit} vs outbound IPv4 {pub} "
                "(update etc/public_host.txt or run links --public-host)."
            )
        return lines

    ips, err = _ipv4_a_records(host)
    if err:
        lines.append(f"  DNS for {host}: failed ({err})")
        return lines
    if not ips:
        lines.append(f"  DNS for {host}: no A records")
        return lines

    sorted_ips = ", ".join(sorted(ips))
    if not pub:
        lines.append(f"  {host} A record(s): {sorted_ips}")
        lines.append("  Outbound IPv4: (could not detect)")
        return lines

    if pub in ips:
        lines.append(
            f"  Match: outbound IPv4 {pub} matches A record(s) for {host} ({sorted_ips})."
        )
    else:
        lines.append(
            f"  Mismatch: outbound IPv4 {pub} not in A record(s) for {host}: {sorted_ips}."
        )
        lines.append(
            "  Hint: run `tulipbridge update` (Cloudflare DDNS), wait for DNS TTL, "
            "then `tulipbridge links`."
        )
    return lines
