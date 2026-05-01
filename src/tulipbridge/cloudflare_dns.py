"""Optional Cloudflare DNS A-record updates for DDNS (Phase 4 thin slice)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from tulipbridge import __version__
from tulipbridge.paths import etc_dir

_CF_API_BASE = "https://api.cloudflare.com/client/v4"
_LAST_IP_FILENAME = "last_cloudflare_ip.txt"
_CF_JSON_FILENAME = "cloudflare.json"
_DNS_TTL = 120
_HTTP_TIMEOUT = 15.0


def last_cloudflare_ip_path() -> Path:
    """Path to cached last successfully pushed IPv4."""
    return etc_dir() / _LAST_IP_FILENAME


def read_cached_ip() -> str | None:
    path = last_cloudflare_ip_path()
    if not path.is_file():
        return None
    try:
        s = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return s if s else None


def write_cached_ip(ip: str) -> None:
    path = last_cloudflare_ip_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(ip.strip() + "\n", encoding="utf-8")


def cloudflare_json_path() -> Path:
    return etc_dir() / _CF_JSON_FILENAME


def read_cloudflare_json_file() -> dict[str, str]:
    """Load optional ``etc/cloudflare.json`` (merged with env; use POSIX mode 600)."""
    path = cloudflare_json_path()
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for key in ("api_token", "zone_id", "record_name"):
        val = raw.get(key)
        if isinstance(val, str) and val.strip():
            out[key] = val.strip()

    if os.name == "posix":
        try:
            path.chmod(0o600)
        except OSError:
            pass
    return out


def write_cloudflare_json_file(token: str, zone_id: str, record_name: str) -> Path:
    """Write ``etc/cloudflare.json``. On POSIX sets mode 600; schema matches the reader."""
    path = cloudflare_json_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "api_token": token.strip(),
        "zone_id": zone_id.strip(),
        "record_name": record_name.strip(),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if os.name == "posix":
        try:
            path.chmod(0o600)
        except OSError:
            pass
    return path


def cloudflare_env() -> tuple[str, str, str] | None:
    """Return (token, zone_id, fqdn) from env; unset fields fall back to ``etc/cloudflare.json``."""
    file_v = read_cloudflare_json_file()
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip() or file_v.get(
        "api_token", ""
    )
    zone = os.environ.get("CLOUDFLARE_ZONE_ID", "").strip() or file_v.get("zone_id", "")
    name = os.environ.get("CLOUDFLARE_RECORD_NAME", "").strip() or file_v.get(
        "record_name", ""
    )
    if not token or not zone or not name:
        return None
    return token, zone, name


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": f"tulipbridge/{__version__}",
    }


def _request_json(
    method: str,
    url: str,
    token: str,
    body: dict[str, Any] | None = None,
) -> tuple[bool, dict[str, Any] | str]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = Request(url, data=data, method=method, headers=_headers(token))
    try:
        with urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            code = getattr(resp, "status", None) or resp.getcode()
            if code != 200:
                return False, f"HTTP {code}: {raw[:500]}"
            out = json.loads(raw)
    except HTTPError as e:
        try:
            body_txt = e.read().decode("utf-8", errors="replace")
            err_json = json.loads(body_txt)
            errs = err_json.get("errors") or []
            msg = errs[0].get("message", body_txt) if errs else body_txt
        except (json.JSONDecodeError, ValueError, IndexError):
            msg = str(e)
        return False, msg
    except (URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        return False, str(e)

    if isinstance(out, dict) and out.get("success") is False:
        errs = out.get("errors") or []
        msg = errs[0].get("message", str(out)) if errs else str(out)
        return False, msg
    return True, out


def find_a_record_id(token: str, zone_id: str, fqdn: str) -> tuple[str | None, str | None]:
    """Return DNS record id for the sole A record named ``fqdn``, or error message."""
    qname = quote(fqdn, safe="")
    url = f"{_CF_API_BASE}/zones/{zone_id}/dns_records?name={qname}&type=A"
    ok, payload = _request_json("GET", url, token)
    if not ok:
        return None, str(payload)

    assert isinstance(payload, dict)
    results = payload.get("result")
    if not isinstance(results, list) or not results:
        return None, "no A record found for this name (create one in Cloudflare first)"

    if len(results) > 1:
        # Thin slice: first record only; operator should dedupe in dashboard.
        pass

    rid = results[0].get("id")
    if not isinstance(rid, str) or not rid.strip():
        return None, "unexpected API response (missing record id)"
    return rid.strip(), None


def patch_a_record(token: str, zone_id: str, record_id: str, ipv4: str) -> tuple[bool, str]:
    """PATCH A record content + TTL."""
    url = f"{_CF_API_BASE}/zones/{zone_id}/dns_records/{record_id}"
    body = {"content": ipv4.strip(), "ttl": _DNS_TTL}
    ok, payload = _request_json("PATCH", url, token, body)
    if not ok:
        return False, str(payload)
    return True, ""


def cloudflare_update_lines(public_ipv4: str | None) -> list[str]:
    """
    Lines to print after ``update`` summary when Cloudflare DDNS is optional.

    Uses env: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ZONE_ID, CLOUDFLARE_RECORD_NAME.
    """
    if not public_ipv4 or not str(public_ipv4).strip():
        return [
            "Cloudflare DNS: skipped (no public IPv4 detected).",
        ]

    ip = str(public_ipv4).strip()
    env = cloudflare_env()
    if env is None:
        return [
            "Cloudflare DNS: skipped (set CLOUDFLARE_* env vars or etc/cloudflare.json — "
            "see README).",
        ]

    token, zone_id, fqdn = env
    cached = read_cached_ip()
    if cached == ip:
        return [
            "Cloudflare DNS: skipped (cached IP unchanged).",
        ]

    rid, err = find_a_record_id(token, zone_id, fqdn)
    if err:
        return [f"Cloudflare DNS: failed to find A record — {err}"]
    assert rid is not None

    ok, msg = patch_a_record(token, zone_id, rid, ip)
    if ok:
        write_cached_ip(ip)
        lines = [
            f"Cloudflare DNS: updated A record for {fqdn} -> {ip} (TTL {_DNS_TTL}).",
        ]
        return lines

    return [f"Cloudflare DNS: PATCH failed — {msg}"]
