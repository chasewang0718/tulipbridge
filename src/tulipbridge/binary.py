"""Download and manage the sing-box executable from GitHub Releases."""

from __future__ import annotations

import io
import json
import os
import platform
import re
import shutil
import stat
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from tulipbridge.paths import bin_dir, singbox_bin, version_file

GITHUB_API_LATEST = "https://api.github.com/repos/SagerNet/sing-box/releases/latest"
GITHUB_API_TAG = "https://api.github.com/repos/SagerNet/sing-box/releases/tags/{tag}"

USER_AGENT = "tulipbridge/0.1 (sing-box installer)"


class BinaryDownloadError(RuntimeError):
    """Failed to download or install sing-box."""


def _request_json(url: str) -> dict[str, Any]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise BinaryDownloadError(f"GitHub API error {e.code}: {url}") from e
    except urllib.error.URLError as e:
        raise BinaryDownloadError(f"Network error fetching {url}: {e}") from e


def _normalize_version(tag_or_version: str) -> str:
    return tag_or_version.lstrip("v").strip()


def _detect_os_arch() -> tuple[str, str]:
    sys_name = sys.platform
    if sys_name == "win32":
        os_name = "windows"
    elif sys_name == "darwin":
        os_name = "darwin"
    elif sys_name.startswith("linux"):
        os_name = "linux"
    else:
        raise BinaryDownloadError(f"Unsupported platform: {sys_name}")

    machine = platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        arch = "amd64"
    elif machine in ("aarch64", "arm64"):
        arch = "arm64"
    elif machine in ("armv7l",):
        arch = "armv7"
    elif machine in ("i386", "i686"):
        arch = "386"
    else:
        raise BinaryDownloadError(f"Unsupported architecture: {machine}")

    return os_name, arch


def _asset_regex(os_name: str, arch: str) -> re.Pattern[str]:
    # sing-box-1.12.25-windows-amd64.zip or sing-box-1.12.25-linux-amd64.tar.gz
    return re.compile(
        rf"^sing-box-[\w.-]+-{re.escape(os_name)}-{re.escape(arch)}\.(zip|tar\.gz)$",
        re.IGNORECASE,
    )


def _pick_asset(release: dict[str, Any]) -> tuple[str, str]:
    """Return (browser_download_url, asset_name)."""
    os_name, arch = _detect_os_arch()
    pattern = _asset_regex(os_name, arch)
    assets = release.get("assets") or []
    for a in assets:
        name = a.get("name") or ""
        url = a.get("browser_download_url") or ""
        if pattern.match(name) and url:
            return url, name
    raise BinaryDownloadError(
        f"No sing-box asset for {os_name}-{arch} in release "
        f"{release.get('tag_name', '?')}. Install sing-box manually into {bin_dir()}."
    )


def fetch_latest_release() -> dict[str, Any]:
    return _request_json(GITHUB_API_LATEST)


def fetch_release_by_tag(tag: str) -> dict[str, Any]:
    tag = tag if tag.startswith("v") else f"v{tag}"
    return _request_json(GITHUB_API_TAG.format(tag=tag))


def singbox_version() -> str | None:
    vf = version_file()
    if not vf.is_file():
        return None
    return _normalize_version(vf.read_text(encoding="utf-8"))


def _download_url_to_file(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=600) as resp:
        dest.write_bytes(resp.read())


def _find_executable_in_tar(data: bytes, want_name: str) -> bytes | None:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            base = os.path.basename(m.name)
            if base == want_name:
                extracted = tf.extractfile(m)
                if extracted is None:
                    continue
                return extracted.read()
    return None


def _extract_singbox_payload(archive_path: Path, dest_bin: Path) -> None:
    want = "sing-box.exe" if sys.platform == "win32" else "sing-box"
    data = archive_path.read_bytes()
    name_lower = archive_path.name.lower()
    payload: bytes | None = None

    if name_lower.endswith(".tar.gz") or name_lower.endswith(".tgz"):
        payload = _find_executable_in_tar(data, want)
    elif name_lower.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for name in zf.namelist():
                base = os.path.basename(name)
                if base == want:
                    payload = zf.read(name)
                    break
            if payload is None:
                for name in zf.namelist():
                    base = os.path.basename(name)
                    if base in ("sing-box", "sing-box.exe"):
                        payload = zf.read(name)
                        break

    if payload is None:
        raise BinaryDownloadError(f"Could not find sing-box binary inside {archive_path.name}")

    dest_bin.parent.mkdir(parents=True, exist_ok=True)
    dest_bin.write_bytes(payload)
    if sys.platform != "win32":
        mode = dest_bin.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        dest_bin.chmod(mode)


def download_singbox(version: str | None = None) -> Path:
    """
    Download sing-box from GitHub Releases into ~/.tulipbridge/bin/.
    Returns path to the sing-box executable.
    """
    ensure_bin = bin_dir()
    ensure_bin.mkdir(parents=True, exist_ok=True)
    dest = singbox_bin()

    if version:
        release = fetch_release_by_tag(version)
    else:
        release = fetch_latest_release()

    tag = release.get("tag_name") or ""
    ver_normalized = _normalize_version(tag)
    url, asset_name = _pick_asset(release)

    with tempfile.TemporaryDirectory(prefix="tulipbridge-singbox-") as tmp:
        archive = Path(tmp) / asset_name
        _download_url_to_file(url, archive)
        tmp_bin = Path(tmp) / ("sing-box.exe" if sys.platform == "win32" else "sing-box")
        _extract_singbox_payload(archive, tmp_bin)
        shutil.move(str(tmp_bin), str(dest))

    version_file().write_text(ver_normalized + "\n", encoding="utf-8")
    return dest


def ensure_singbox(version: str | None = None) -> Path:
    """
    Ensure sing-box exists in ~/.tulipbridge/bin/.
    If the binary is missing, or VERSION differs from the requested release, downloads.
    """
    dest = singbox_bin()
    if version:
        want = _normalize_version(version)
        current = singbox_version()
        if dest.is_file() and current == want:
            return dest
        return download_singbox(version)

    release = fetch_latest_release()
    tag = release.get("tag_name") or ""
    latest_ver = _normalize_version(tag)

    if dest.is_file() and singbox_version() == latest_ver:
        return dest

    return download_singbox(None)
