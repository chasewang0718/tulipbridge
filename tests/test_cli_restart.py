"""Tests for `tulipbridge restart`."""

from __future__ import annotations

import argparse
from unittest.mock import patch

import pytest

from tulipbridge import cli
from tulipbridge.paths import set_data_root


@pytest.fixture
def isolated_home(tmp_path):
    set_data_root(tmp_path)
    yield tmp_path
    set_data_root(None)


def test_restart_errors_without_config(isolated_home) -> None:
    code = cli._cmd_restart(argparse.Namespace())
    assert code == 1


def test_restart_starts_when_stopped(isolated_home) -> None:
    isolated_home.joinpath("etc").mkdir(parents=True)
    isolated_home.joinpath("etc", "config.json").write_text("{}", encoding="utf-8")

    with patch("tulipbridge.cli.is_running", return_value=False):
        with patch("tulipbridge.cli.stop_singbox") as stop:
            with patch("tulipbridge.cli.start_singbox", return_value=4242) as start:
                code = cli._cmd_restart(argparse.Namespace())

    assert code == 0
    stop.assert_not_called()
    start.assert_called_once()


def test_restart_stops_then_starts_when_running(isolated_home) -> None:
    isolated_home.joinpath("etc").mkdir(parents=True)
    isolated_home.joinpath("etc", "config.json").write_text("{}", encoding="utf-8")

    with patch("tulipbridge.cli.is_running", return_value=True):
        with patch("tulipbridge.cli.stop_singbox") as stop:
            with patch("tulipbridge.cli.start_singbox", return_value=4243) as start:
                code = cli._cmd_restart(argparse.Namespace())

    assert code == 0
    stop.assert_called_once()
    start.assert_called_once()
