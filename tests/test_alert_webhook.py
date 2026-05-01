"""Tests for optional webhook alerts."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tulipbridge.alert_webhook import run_alert_once
from tulipbridge.paths import set_data_root


@pytest.fixture
def isolated_home(tmp_path):
    set_data_root(tmp_path)
    yield tmp_path
    set_data_root(None)


def _clear_bark(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TULIPBRIDGE_ALERT_BARK_KEY", raising=False)
    monkeypatch.delenv("TULIPBRIDGE_ALERT_BARK_URL", raising=False)


def test_alert_skips_no_pid(isolated_home, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_bark(monkeypatch)
    monkeypatch.setenv("TULIPBRIDGE_ALERT_WEBHOOK", "http://example.com/hook")
    code = run_alert_once()
    assert code == 0


def test_alert_skips_when_running(isolated_home, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_bark(monkeypatch)
    monkeypatch.setenv("TULIPBRIDGE_ALERT_WEBHOOK", "http://example.com/hook")
    pf = isolated_home / "sing-box.pid"
    pf.write_text("999999\n", encoding="utf-8")
    with patch("tulipbridge.alert_webhook.is_running", return_value=True):
        code = run_alert_once()
    assert code == 0


def test_alert_posts_when_stale(isolated_home, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_bark(monkeypatch)
    monkeypatch.setenv("TULIPBRIDGE_ALERT_WEBHOOK", "http://example.com/hook")
    pf = isolated_home / "sing-box.pid"
    pf.write_text("999999\n", encoding="utf-8")

    with patch("tulipbridge.alert_webhook.is_running", return_value=False):
        with patch("tulipbridge.alert_webhook.urlopen") as uo:
            uo.return_value.__enter__.return_value.getcode = MagicMock(return_value=200)
            uo.return_value.__enter__.return_value.status = 200
            code = run_alert_once()

    assert code == 0
    assert uo.called


def test_alert_no_channels_when_stale(isolated_home, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TULIPBRIDGE_ALERT_WEBHOOK", raising=False)
    monkeypatch.delenv("TULIPBRIDGE_ALERT_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TULIPBRIDGE_ALERT_TELEGRAM_CHAT_ID", raising=False)
    _clear_bark(monkeypatch)
    pf = isolated_home / "sing-box.pid"
    pf.write_text("999999\n", encoding="utf-8")
    with patch("tulipbridge.alert_webhook.is_running", return_value=False):
        with patch("tulipbridge.alert_webhook.urlopen") as uo:
            code = run_alert_once()
    assert code == 0
    assert not uo.called


def test_alert_telegram_when_stale(isolated_home, monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_bark(monkeypatch)
    monkeypatch.delenv("TULIPBRIDGE_ALERT_WEBHOOK", raising=False)
    monkeypatch.setenv("TULIPBRIDGE_ALERT_TELEGRAM_BOT_TOKEN", "123456:ABC")
    monkeypatch.setenv("TULIPBRIDGE_ALERT_TELEGRAM_CHAT_ID", "987654")
    pf = isolated_home / "sing-box.pid"
    pf.write_text("999999\n", encoding="utf-8")

    with patch("tulipbridge.alert_webhook.is_running", return_value=False):
        with patch("tulipbridge.alert_webhook.urlopen") as uo:
            cm = MagicMock()
            cm.__enter__.return_value.read.return_value = b'{"ok":true}'
            cm.__enter__.return_value.getcode = MagicMock(return_value=200)
            cm.__enter__.return_value.status = 200
            uo.return_value = cm
            code = run_alert_once()

    assert code == 0
    assert uo.called
    called_urls = [str(call.args[0].full_url) for call in uo.call_args_list]
    assert any("api.telegram.org" in u for u in called_urls)


def test_alert_bark_when_stale(isolated_home, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TULIPBRIDGE_ALERT_WEBHOOK", raising=False)
    monkeypatch.delenv("TULIPBRIDGE_ALERT_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TULIPBRIDGE_ALERT_TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("TULIPBRIDGE_ALERT_BARK_URL", raising=False)
    monkeypatch.setenv("TULIPBRIDGE_ALERT_BARK_KEY", "deviceKey123")
    pf = isolated_home / "sing-box.pid"
    pf.write_text("999999\n", encoding="utf-8")

    with patch("tulipbridge.alert_webhook.is_running", return_value=False):
        with patch("tulipbridge.alert_webhook.urlopen") as uo:
            cm = MagicMock()
            cm.__enter__.return_value.getcode = MagicMock(return_value=200)
            cm.__enter__.return_value.status = 200
            uo.return_value = cm
            code = run_alert_once()

    assert code == 0
    assert uo.called
    called_urls = [str(call.args[0].full_url) for call in uo.call_args_list]
    assert any("api.day.app" in u for u in called_urls)


def test_alert_bark_custom_url_when_stale(
    isolated_home, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("TULIPBRIDGE_ALERT_WEBHOOK", raising=False)
    monkeypatch.delenv("TULIPBRIDGE_ALERT_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TULIPBRIDGE_ALERT_TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("TULIPBRIDGE_ALERT_BARK_KEY", raising=False)
    monkeypatch.setenv("TULIPBRIDGE_ALERT_BARK_URL", "https://push.example.net/mydevice")
    pf = isolated_home / "sing-box.pid"
    pf.write_text("999999\n", encoding="utf-8")

    with patch("tulipbridge.alert_webhook.is_running", return_value=False):
        with patch("tulipbridge.alert_webhook.urlopen") as uo:
            cm = MagicMock()
            cm.__enter__.return_value.getcode = MagicMock(return_value=200)
            cm.__enter__.return_value.status = 200
            uo.return_value = cm
            code = run_alert_once()

    assert code == 0
    assert uo.called
    called_urls = [str(call.args[0].full_url) for call in uo.call_args_list]
    assert any("push.example.net" in u for u in called_urls)
