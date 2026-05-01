"""Generate self-signed TLS cert/key for QUIC inbounds (Hy2 / TUIC)."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

_TLS_KEY_RE = re.compile(
    r"(-----BEGIN PRIVATE KEY-----.*?-----END PRIVATE KEY-----)",
    re.DOTALL,
)
_TLS_CERT_RE = re.compile(
    r"(-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----)",
    re.DOTALL,
)


class TLSGenerationError(RuntimeError):
    """Failed to create TLS certificate files."""


def _parse_tls_pem(stdout: str) -> tuple[str, str]:
    km = _TLS_KEY_RE.search(stdout)
    cm = _TLS_CERT_RE.search(stdout)
    if not km or not cm:
        raise TLSGenerationError(
            "Could not parse sing-box tls-keypair output (expected PEM key and certificate)."
        )
    return km.group(1).strip() + "\n", cm.group(1).strip() + "\n"


def _openssl_fallback(server_name: str, cert_path: Path, key_path: Path) -> None:
    openssl = shutil.which("openssl")
    if not openssl:
        raise TLSGenerationError(
            "Neither sing-box tls-keypair nor openssl is available. "
            "Install openssl or ensure sing-box is installed."
        )
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    cnf = cert_path.parent / "openssl-san.cnf"
    cnf.write_text(
        f"""[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = {server_name}

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = {server_name}
""",
        encoding="utf-8",
    )
    subprocess.run(
        [
            openssl,
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-keyout",
            str(key_path),
            "-out",
            str(cert_path),
            "-days",
            "825",
            "-nodes",
            "-config",
            str(cnf),
            "-extensions",
            "v3_req",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )


def ensure_tls_cert_pair(
    singbox_bin: Path,
    server_name: str,
    *,
    cert_path: Path,
    key_path: Path,
) -> tuple[Path, Path]:
    """
    Write TLS certificate and private key for Hy2/TUIC listeners.

    Prefer ``sing-box generate tls-keypair <server_name>``; fall back to openssl.
    """
    if cert_path.is_file() and key_path.is_file():
        return cert_path, key_path

    cert_path.parent.mkdir(parents=True, exist_ok=True)

    if singbox_bin.is_file():
        proc = subprocess.run(
            [str(singbox_bin), "generate", "tls-keypair", server_name],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout:
            try:
                key_pem, cert_pem = _parse_tls_pem(proc.stdout)
            except TLSGenerationError:
                pass
            else:
                key_path.write_text(key_pem, encoding="utf-8")
                cert_path.write_text(cert_pem, encoding="utf-8")
                return cert_path, key_path

    try:
        _openssl_fallback(server_name, cert_path, key_path)
    except (TLSGenerationError, subprocess.CalledProcessError, FileNotFoundError) as e:
        err = ""
        if isinstance(e, subprocess.CalledProcessError):
            err = (e.stderr or e.stdout or "").strip()
        raise TLSGenerationError(
            f"TLS generation failed: {e}" + (f" ({err})" if err else "")
        ) from e

    return cert_path, key_path
