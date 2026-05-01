"""Fetch optional sing-box Clash API ``/memory`` for ``status`` (experimental.clash_api)."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from tulipbridge import __version__

_TIMEOUT_SEC = 3.0


def clash_memory_status_lines(cfg: dict[str, Any]) -> list[str]:
    """Return 0–3 lines summarizing Clash API memory, or empty if not configured."""
    exp = cfg.get("experimental")
    if not isinstance(exp, dict):
        return []

    ca = exp.get("clash_api")
    if not isinstance(ca, dict):
        return []

    ctrl = str(ca.get("external_controller", "")).strip()
    secret = str(ca.get("secret", "")).strip()
    if not ctrl:
        return []

    host_part = ctrl.replace("http://", "").replace("https://", "").split("/")[0].strip()
    url = f"http://{host_part}/memory"

    headers = {"User-Agent": f"tulipbridge/{__version__}"}
    if secret:
        headers["Authorization"] = f"Bearer {secret}"

    req = Request(url, headers=headers, method="GET")
    lines = ["", "Clash API (stats hint):"]
    try:
        with urlopen(req, timeout=_TIMEOUT_SEC) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            code = getattr(resp, "status", None) or resp.getcode()
            if code != 200:
                lines.append(f"  HTTP {code}: {raw[:120]}")
                return lines
        try:
            data = json.loads(raw)
            snippet = json.dumps(data, ensure_ascii=False)[:240]
            lines.append(f"  /memory: {snippet}")
        except json.JSONDecodeError:
            lines.append(f"  /memory (non-JSON): {raw[:200]}")
    except URLError as e:
        lines.append(f"  unreachable ({e})")

    return lines
