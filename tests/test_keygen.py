"""Tests for key generation (mock sing-box subprocess)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tulipbridge.keygen import (
    KeyGenerationError,
    generate_keys,
    load_keys,
    save_keys,
)
from tulipbridge.paths import keys_json_path, set_data_root


@pytest.fixture
def isolated_home(tmp_path: Path):
    set_data_root(tmp_path)
    yield tmp_path
    set_data_root(None)


_FAKE_KEYPAIR_OUT = """PrivateKey: AbCdEfGhIjKlMnOpQrStUvWxYz0123456789abcd
PublicKey: ZyXwVuTsRqPoNmLkJiHgFeDcBa0987654321zyxw
"""


def test_generate_keys_parses_and_persists(isolated_home: Path) -> None:
    fake_bin = isolated_home / "sing-box"
    fake_bin.write_bytes(b"")

    with patch("tulipbridge.keygen.subprocess.run") as run:
        run.return_value = MagicMock(returncode=0, stdout=_FAKE_KEYPAIR_OUT, stderr="")
        with patch("tulipbridge.keygen.secrets.token_hex", return_value="11223344"):
            keys = generate_keys(fake_bin)

    assert keys["reality_private_key"].startswith("AbCdEf")
    assert keys["reality_public_key"].startswith("ZyXwVu")
    assert keys["short_id"] == "11223344"
    assert "uuid" in keys

    loaded = load_keys()
    assert loaded is not None
    assert loaded["reality_public_key"] == keys["reality_public_key"]
    assert keys_json_path().is_file()


def test_generate_keys_subprocess_failure(isolated_home: Path) -> None:
    fake_bin = isolated_home / "sing-box"
    fake_bin.write_bytes(b"")

    with patch("tulipbridge.keygen.subprocess.run") as run:
        run.return_value = MagicMock(returncode=1, stdout="", stderr="boom")
        with pytest.raises(KeyGenerationError, match="reality-keypair"):
            generate_keys(fake_bin)


def test_generate_keys_bad_stdout(isolated_home: Path) -> None:
    fake_bin = isolated_home / "sing-box"
    fake_bin.write_bytes(b"")

    with patch("tulipbridge.keygen.subprocess.run") as run:
        run.return_value = MagicMock(returncode=0, stdout="no keys here\n", stderr="")
        with pytest.raises(KeyGenerationError, match="Could not parse"):
            generate_keys(fake_bin)


def test_save_keys_roundtrip(isolated_home: Path) -> None:
    data = {
        "uuid": "550e8400-e29b-41d4-a716-446655440000",
        "reality_private_key": "priv",
        "reality_public_key": "pub",
        "short_id": "01020304",
    }
    save_keys(data)
    got = load_keys()
    assert got == data


def test_missing_singbox_binary(isolated_home: Path) -> None:
    missing = isolated_home / "missing-sing-box"
    with pytest.raises(KeyGenerationError, match="not found"):
        generate_keys(missing)
