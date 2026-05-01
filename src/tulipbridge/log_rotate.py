"""Rotate ``logs/sing-box.log`` when it exceeds a size threshold (stdlib only)."""

from __future__ import annotations

import os

from tulipbridge.paths import singbox_log_path

_ENV_MAX_BYTES = "TULIPBRIDGE_LOG_MAX_BYTES"
_DEFAULT_MAX_BYTES = 10 * 1024 * 1024


def _max_bytes() -> int:
    raw = os.environ.get(_ENV_MAX_BYTES, "").strip()
    if raw.isdigit():
        return max(1024, int(raw))
    return _DEFAULT_MAX_BYTES


def rotate_singbox_log(*, max_bytes: int | None = None) -> tuple[bool, str]:
    """
    If ``sing-box.log`` exists and is larger than ``max_bytes``, rename it to
    ``sing-box.log.1`` (overwrite previous backup) and create an empty log file.

    Returns ``(did_rotate, message)``.
    """
    limit = _max_bytes() if max_bytes is None else max(1024, max_bytes)
    path = singbox_log_path()
    if not path.is_file():
        return False, f"No log file at {path}."
    size = path.stat().st_size
    if size <= limit:
        return False, f"Log size {size} bytes (limit {limit}); no rotation."

    backup = path.with_suffix(path.suffix + ".1")
    try:
        if backup.is_file():
            backup.unlink()
    except OSError as e:
        return False, f"Could not remove old backup: {e}"

    try:
        path.rename(backup)
        path.touch()
    except OSError as e:
        return False, f"Rotation failed: {e}"

    return True, f"Rotated {size} bytes -> {backup.name}"


def rotate_lines() -> list[str]:
    """Human-readable lines for CLI output."""
    did, msg = rotate_singbox_log()
    return [f"Log rotation: {msg}"]
