"""Optional webhook / Telegram / Bark alert when sing-box PID file is stale (Phase 5 thin slice)."""

from __future__ import annotations

import json
import os
import socket
from datetime import datetime, timezone
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from tulipbridge.paths import pid_file_path
from tulipbridge.process import is_running

_WEBHOOK_ENV = "TULIPBRIDGE_ALERT_WEBHOOK"
_TELEGRAM_TOKEN_ENV = "TULIPBRIDGE_ALERT_TELEGRAM_BOT_TOKEN"
_TELEGRAM_CHAT_ENV = "TULIPBRIDGE_ALERT_TELEGRAM_CHAT_ID"
_BARK_KEY_ENV = "TULIPBRIDGE_ALERT_BARK_KEY"
_BARK_URL_ENV = "TULIPBRIDGE_ALERT_BARK_URL"
_HTTP_TIMEOUT = 15.0
_BARK_HTTP_TIMEOUT = 10.0


def _bark_get_url(title: str, body: str) -> str | None:
    """Build Bark HTTPS GET URL (official pattern or custom base via env)."""
    bark_base = os.environ.get(_BARK_URL_ENV, "").strip()
    bark_key = os.environ.get(_BARK_KEY_ENV, "").strip()
    t = quote(title, safe="")
    b = quote(body, safe="")
    if bark_base:
        return f"{bark_base.rstrip('/')}/{t}/{b}"
    if bark_key:
        k = quote(bark_key, safe="")
        return f"https://api.day.app/{k}/{t}/{b}"
    return None


def run_alert_once() -> int:
    """
    If PID file exists but process is not running, send optional webhook, Telegram, and/or Bark.

    Does not alert when there is no PID file (nothing registered as started).
    Exit code always 0 for scripting friendliness.
    """
    url = os.environ.get(_WEBHOOK_ENV, "").strip()
    tg_token = os.environ.get(_TELEGRAM_TOKEN_ENV, "").strip()
    tg_chat = os.environ.get(_TELEGRAM_CHAT_ENV, "").strip()
    pf = pid_file_path()

    if not pf.is_file():
        print("Alert: skipped (no PID file).")
        return 0

    if is_running():
        print("Alert: skipped (sing-box running).")
        return 0

    host = socket.gethostname()
    ts = datetime.now(timezone.utc).isoformat()
    payload = {
        "hostname": host,
        "sing_box": "stale_pid",
        "time_utc": ts,
    }

    bark_configured = bool(
        os.environ.get(_BARK_URL_ENV, "").strip() or os.environ.get(_BARK_KEY_ENV, "").strip()
    )

    if not url and not (tg_token and tg_chat) and not bark_configured:
        print(
            "Alert: stale PID file — set "
            f"{_WEBHOOK_ENV} and/or {_TELEGRAM_TOKEN_ENV}+{_TELEGRAM_CHAT_ENV} "
            f"and/or {_BARK_KEY_ENV} (or {_BARK_URL_ENV})."
        )
        return 0

    if url:
        body = json.dumps(payload).encode("utf-8")
        req = Request(
            url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "tulipbridge/alert"},
        )
        try:
            with urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
                code = getattr(resp, "status", None) or resp.getcode()
                if code != 200:
                    print(f"Alert: webhook returned HTTP {code}.")
                else:
                    print("Alert: webhook POST ok.")
        except URLError as e:
            print(f"Alert: webhook failed: {e}")

    if tg_token and tg_chat:
        text = (
            f"TulipBridge: stale sing-box PID on {host} ({ts}). "
            "Check the server and run `tulipbridge status`."
        )
        tg_body = json.dumps(
            {"chat_id": tg_chat, "text": text},
            ensure_ascii=False,
        ).encode("utf-8")
        tg_url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
        req_tg = Request(
            tg_url,
            data=tg_body,
            method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "tulipbridge/alert"},
        )
        try:
            with urlopen(req_tg, timeout=_HTTP_TIMEOUT) as resp:
                code = getattr(resp, "status", None) or resp.getcode()
                if code != 200:
                    raw = resp.read().decode("utf-8", errors="replace")[:300]
                    print(f"Alert: Telegram API HTTP {code}: {raw}")
                else:
                    print("Alert: Telegram sendMessage ok.")
        except URLError as e:
            print(f"Alert: Telegram failed: {e}")

    bark_target = _bark_get_url(
        "TulipBridge",
        f"stale sing-box PID on {host} ({ts}). Check server; run tulipbridge status.",
    )
    if bark_target:
        req_bark = Request(
            bark_target,
            method="GET",
            headers={"User-Agent": "tulipbridge/alert"},
        )
        try:
            with urlopen(req_bark, timeout=_BARK_HTTP_TIMEOUT) as resp:
                code = getattr(resp, "status", None) or resp.getcode()
                if code != 200:
                    print(f"Alert: Bark returned HTTP {code}.")
                else:
                    print("Alert: Bark GET ok.")
        except URLError as e:
            print(f"Alert: Bark failed: {e}")

    return 0
