"""Fetch public IPv4 via HTTPS (no extra dependencies)."""

from __future__ import annotations

import ipaddress
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Plain-text IPv4 endpoints (fallback order).
_PUBLIC_IPV4_URLS = (
    "https://api.ipify.org",
    "https://ifconfig.me/ip",
)

_IPV4_RE = re.compile(
    r"^(?P<ip>\d{1,3}(?:\.\d{1,3}){3})\s*$",
    re.MULTILINE,
)


def _parse_ipv4_line(text: str) -> str | None:
    """Extract first plausible IPv4 from response body."""
    raw = text.strip()
    if not raw:
        return None
    first = raw.splitlines()[0].strip()
    try:
        addr = ipaddress.ip_address(first)
    except ValueError:
        m = _IPV4_RE.search(raw)
        if not m:
            return None
        addr = ipaddress.ip_address(m.group("ip"))
    if not isinstance(addr, ipaddress.IPv4Address):
        return None
    return str(addr)


def fetch_public_ipv4(*, timeout: float = 5.0) -> str | None:
    """
    Best-effort public IPv4 as seen by external HTTPS reflectors.

    Returns ``None`` if every endpoint fails or no valid IPv4 is returned.
    """
    for url in _PUBLIC_IPV4_URLS:
        try:
            req = Request(url, method="GET", headers={"User-Agent": "tulipbridge/network_public"})
            with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — curated HTTPS URLs only
                code = getattr(resp, "status", None) or resp.getcode()
                if code != 200:
                    continue
                body = resp.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError, OSError, ValueError):
            continue
        parsed = _parse_ipv4_line(body)
        if parsed:
            return parsed
    return None


def ipv4_lookup_note(ip: str) -> str | None:
    """Optional extra line when the returned IPv4 is unusual (e.g. CGNAT range)."""
    try:
        addr = ipaddress.ip_address(ip.strip())
    except ValueError:
        return None
    if not isinstance(addr, ipaddress.IPv4Address):
        return None
    if addr in ipaddress.ip_network("100.64.0.0/10"):
        return (
            "Note: this address is in 100.64.0.0/10 (RFC 6598 shared space); "
            "unusual as an external lookup — verify your network path."
        )
    return None
