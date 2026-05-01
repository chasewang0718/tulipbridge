"""Runtime directory layout for TulipBridge (default ~/.tulipbridge, override for portable use)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Process-local override set by CLI `--data-dir` / `--portable` (highest priority).
_override_root: Path | None = None

_ENV_VAR = "TULIPBRIDGE_HOME"
_DEFAULT_RELATIVE = Path.home() / ".tulipbridge"
_PORTABLE_DIRNAME = "tulipbridge-data"


def set_data_root(path: Path | str | None) -> None:
    """Pin all TulipBridge paths under this directory for the current process.

    Pass ``None`` to clear an override and fall back to env / default.
    """
    global _override_root
    if path is None:
        _override_root = None
        return
    _override_root = Path(path).expanduser().resolve()


def get_tulipbridge_home() -> Path:
    """Base directory for bin/, etc/, logs/, subscribe/, sing-box.pid.

    Precedence:
    1. ``set_data_root()`` (from ``--data-dir`` / ``--portable``)
    2. Environment variable ``TULIPBRIDGE_HOME``
    3. ``~/.tulipbridge``
    """
    if _override_root is not None:
        return _override_root
    env = os.environ.get(_ENV_VAR, "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return _DEFAULT_RELATIVE.resolve()


def portable_data_path(cwd: Path | None = None) -> Path:
    """Directory used by ``--portable``: ``<cwd>/tulipbridge-data``."""
    base = cwd if cwd is not None else Path.cwd()
    return (base / _PORTABLE_DIRNAME).resolve()


def bin_dir() -> Path:
    return get_tulipbridge_home() / "bin"


def etc_dir() -> Path:
    return get_tulipbridge_home() / "etc"


def logs_dir() -> Path:
    return get_tulipbridge_home() / "logs"


def subscribe_dir() -> Path:
    return get_tulipbridge_home() / "subscribe"


def singbox_bin() -> Path:
    """Path to the sing-box executable for this OS."""
    name = "sing-box.exe" if sys.platform == "win32" else "sing-box"
    return bin_dir() / name


def version_file() -> Path:
    return bin_dir() / "VERSION"


def keys_json_path() -> Path:
    return etc_dir() / "keys.json"


def config_json_path() -> Path:
    return etc_dir() / "config.json"


def pid_file_path() -> Path:
    return get_tulipbridge_home() / "sing-box.pid"


def singbox_log_path() -> Path:
    return logs_dir() / "sing-box.log"


def tls_dir() -> Path:
    """TLS certificate directory under etc/ (Hy2 / TUIC)."""
    return etc_dir() / "tls"


def ensure_dirs() -> None:
    """Create data layout under the active TulipBridge home."""
    root = get_tulipbridge_home()
    for sub in ("bin", "etc", "logs", "subscribe"):
        (root / sub).mkdir(parents=True, exist_ok=True)


def set_keys_json_permissions(path: Path) -> None:
    """Restrict keys.json to owner read/write on POSIX."""
    if os.name != "posix":
        return
    try:
        path.chmod(0o600)
    except OSError:
        pass


# Back-compat / introspection: callable property-like name
def tulipbridge_home() -> Path:
    """Same as :func:`get_tulipbridge_home`."""
    return get_tulipbridge_home()
