# TulipBridge

Python CLI to deploy and manage **sing-box** on a home server (e.g. Netherlands): VLESS-Reality, Hysteria 2, and TUIC v5, with QR/subscription output for clients such as Shadowrocket.

Design goals, protocol choices, network prerequisites, and CLI scope: see [ROADMAP.md](ROADMAP.md).

## Status

**Phase 1–3:** `tulipbridge init` installs sing-box, manages keys under the data directory (`~/.tulipbridge` by default or `--data-dir` / `--portable`), writes `config.json`, runs `sing-box check`, and starts sing-box.

- **VLESS-Reality** (TCP): `--port`, `--sni`
- **Hysteria 2** (UDP): `--hy2-port`, `--hysteria2` / `--no-hysteria2`
- **TUIC v5** (UDP): `--tuic-port`, `--tuic` / `--no-tuic`
- **QUIC TLS** (Hy2/TUIC): self-signed cert via `sing-box generate tls-keypair` (fallback: `openssl`), `--tls-sni`
- **Share links & subscription (Phase 3):** optional `--public-host WAN_IP_OR_DOMAIN` on `init` writes `subscribe/uris-plain.txt`, Base64 `subscribe/subscription.txt`, terminal QR codes, and `subscribe/qr-*.png`. Without `--public-host`, run later: `tulipbridge links --public-host YOUR_HOST` (re-reads `keys.json` + `config.json`, no sing-box restart).
- Other: `--singbox-version`, `--force`

Global options must precede the subcommand: `python -m tulipbridge --portable init`.

**Import on phone:** see [docs/SHADOWROCKET.md](docs/SHADOWROCKET.md) for suggested Shadowrocket versions and import tips (clipboard, PNG QR preferred over terminal QR on Windows).

`update` and `status` are still placeholders (later roadmap phases).

## Install (editable)

```bash
cd tulipbridge
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e .
tulipbridge --help
```

## Requirements

Python 3.10+.

## Portable data directory

By default, binaries and config live under `~/.tulipbridge`. To keep everything in one folder (USB / self-contained repo copy):

- **`--portable`** — uses `./tulipbridge-data` under the **current working directory**. Put global options **before** the subcommand, e.g. `python -m tulipbridge --portable init` (not `init --portable`).
- **`--data-dir PATH`** — same idea but you choose the folder, e.g. `python -m tulipbridge --data-dir D:\tb-data init`.

Environment variable **`TULIPBRIDGE_HOME`** sets the data root when neither flag is used. **`--data-dir` / `--portable` override `TULIPBRIDGE_HOME`** for that process.

Moving to another PC: copy the data directory; on a different OS/architecture, run `init` again so sing-box can download the correct binary.

## Acceptance testing (Phase 1–2)

Manual checklist and pass criteria: [docs/ACCEPTANCE_PHASE1_2.md](docs/ACCEPTANCE_PHASE1_2.md). Automated checks: `pytest tests/ -q`.
