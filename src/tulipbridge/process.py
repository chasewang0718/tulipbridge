"""Start/stop the sing-box subprocess and track PID."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from tulipbridge.paths import pid_file_path, singbox_bin


def _pid_alive(pid: int) -> bool:
    """Return True if a process with PID exists on this OS."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            kernel32.CloseHandle(handle)
            return True
        except OSError:
            return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    else:
        return True


def is_running() -> bool:
    """True if PID file exists and process is alive."""
    pf = pid_file_path()
    if not pf.is_file():
        return False
    try:
        pid = int(pf.read_text(encoding="utf-8").strip())
    except ValueError:
        return False
    return _pid_alive(pid)


def read_pid() -> int | None:
    pf = pid_file_path()
    if not pf.is_file():
        return None
    try:
        return int(pf.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def stop_singbox() -> bool:
    """Stop sing-box when PID file points to a live process.

    Returns True if a running process was stopped or a stale PID file was cleared.
    """
    pf = pid_file_path()
    if not pf.is_file():
        return False
    try:
        pid = int(pf.read_text(encoding="utf-8").strip())
    except ValueError:
        pf.unlink(missing_ok=True)
        return False

    if not _pid_alive(pid):
        pf.unlink(missing_ok=True)
        return False

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pf.unlink(missing_ok=True)
        return False

    # Wait briefly for exit
    for _ in range(50):
        if not _pid_alive(pid):
            break
        time.sleep(0.1)

    if _pid_alive(pid):
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F"],
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
            else:
                os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    pf.unlink(missing_ok=True)
    return True


def start_singbox(config_path: Path, *, log_append: Path | None = None) -> int:
    """
    Start sing-box: `sing-box run -c <config>`.
    Returns child PID. Raises RuntimeError if already running or binary missing.
    """
    if is_running():
        raise RuntimeError("sing-box appears to be already running (PID file present).")

    exe = singbox_bin()
    if not exe.is_file():
        raise RuntimeError(f"sing-box binary not found at {exe}")

    log_path = log_append
    if log_path is None:
        from tulipbridge.paths import singbox_log_path

        log_path = singbox_log_path()

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_f = open(log_path, "ab", buffering=0)

    popen_kwargs: dict[str, object] = {
        "stdin": subprocess.DEVNULL,
        "stdout": log_f,
        "stderr": subprocess.STDOUT,
    }

    if sys.platform == "win32":
        # Run detached from console; keep process after CLI exits
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
        creationflags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
        popen_kwargs["creationflags"] = creationflags
        popen_kwargs["close_fds"] = False
    else:
        popen_kwargs["start_new_session"] = True
        popen_kwargs["close_fds"] = True

    proc = subprocess.Popen(
        [str(exe), "run", "-c", str(config_path)],
        **popen_kwargs,
    )
    log_f.close()

    pid = proc.pid
    pid_file_path().write_text(str(pid) + "\n", encoding="utf-8")

    # Fail fast if sing-box exits immediately (bad config)
    time.sleep(0.4)
    if proc.poll() is not None:
        pid_file_path().unlink(missing_ok=True)
        raise RuntimeError(
            f"sing-box exited immediately with code {proc.returncode}. Check {log_path}."
        )

    return pid
