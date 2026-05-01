"""Integration-style init smoke test with mocked sing-box I/O."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from tulipbridge import cli
from tulipbridge.paths import set_data_root


@pytest.fixture
def isolated_home(tmp_path):
    set_data_root(tmp_path)
    yield tmp_path
    set_data_root(None)


def test_init_smoke_vless_only_mocked_singbox(isolated_home) -> None:
    etc = isolated_home / "etc"
    etc.mkdir(parents=True)
    keys = {
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "reality_private_key": "PrivateKeyLine",
        "reality_public_key": "PublicKeyLine",
        "short_id": "01020304",
    }
    (etc / "keys.json").write_text(json.dumps(keys), encoding="utf-8")

    fake_sb = isolated_home / "sing-box-fake"
    fake_sb.write_bytes(b"")

    with patch("tulipbridge.cli.ensure_singbox", return_value=fake_sb):
        with patch("tulipbridge.cli._validate_singbox_config"):
            with patch("tulipbridge.cli.start_singbox", return_value=4242):
                with patch("tulipbridge.cli.is_running", return_value=False):
                    code = cli.main(
                        [
                            "--data-dir",
                            str(isolated_home),
                            "init",
                            "--no-hysteria2",
                            "--no-tuic",
                            "--public-host",
                            "127.0.0.1",
                            "--port",
                            "8443",
                        ]
                    )

    assert code == 0
    cfg = isolated_home / "etc" / "config.json"
    assert cfg.is_file()
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert any(ib.get("type") == "vless" for ib in data.get("inbounds", []))
