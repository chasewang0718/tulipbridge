# TulipBridge

[![CI](https://github.com/chasewang0718/tulipbridge/actions/workflows/ci.yml/badge.svg)](https://github.com/chasewang0718/tulipbridge/actions/workflows/ci.yml)

Python CLI to deploy and manage **sing-box** on a home server (e.g. Netherlands): VLESS-Reality, Hysteria 2, and TUIC v5, with QR/subscription output for clients such as Shadowrocket.

Design goals, protocol choices, network prerequisites, and CLI scope: see [ROADMAP.md](ROADMAP.md).

**New to this repo / want copy-paste steps on Windows?** See [docs/HANDS_ON_WINDOWS_ZH.md](docs/HANDS_ON_WINDOWS_ZH.md)（手把手，一步一步）.

**China client / async handoff:** if you prep the server in NL first and only test Shadowrocket from China at the end, read [docs/PREP_AND_CHINA_HANDOFF_ZH.md](docs/PREP_AND_CHINA_HANDOFF_ZH.md).

**Quick start:** [docs/QUICKSTART.md](docs/QUICKSTART.md) · **Security:** [docs/SECURITY.md](docs/SECURITY.md) · **Router port forwarding:** [docs/ROUTER_NAT.md](docs/ROUTER_NAT.md) · **External port probe (design):** [docs/PORT_PROBE.md](docs/PORT_PROBE.md)

## Status

**Phase 1–3:** `tulipbridge init` installs sing-box, manages keys under the data directory (`~/.tulipbridge` by default or `--data-dir` / `--portable`), writes `config.json`, runs `sing-box check`, and starts sing-box.

- **VLESS-Reality** (TCP): `--port`, `--sni`
- **Hysteria 2** (UDP): `--hy2-port`, `--hysteria2` / `--no-hysteria2`
- **TUIC v5** (UDP): `--tuic-port`, `--tuic` / `--no-tuic`
- **QUIC TLS** (Hy2/TUIC): self-signed cert via `sing-box generate tls-keypair` (fallback: `openssl`), `--tls-sni`
- **Share links & subscription (Phase 3–4):** optional `--public-host WAN_IP_OR_DOMAIN` on `init` writes `subscribe/uris-plain.txt`, Base64 `subscribe/subscription.txt`, terminal QR codes, and `subscribe/qr-*.png`, and saves the host to `etc/public_host.txt`. Later you can run `tulipbridge links` with **no** `--public-host` to reuse that host, or set `CLOUDFLARE_RECORD_NAME` to your DDNS FQDN so `links` defaults to the domain. You can still pass `--public-host` explicitly to override. Without any saved host or env, use `tulipbridge links --public-host YOUR_HOST` (re-reads `keys.json` + `config.json`, no sing-box restart).
- Other: `--singbox-version`, `--force`

Global options must precede the subcommand: `python -m tulipbridge --portable init`.

**Import on phone:** numbered steps [docs/SHADOWROCKET_IMPORT.md](docs/SHADOWROCKET_IMPORT.md); compatibility matrix [docs/SHADOWROCKET.md](docs/SHADOWROCKET.md) (PNG QR preferred over terminal QR on Windows).

**Phase 4 (thin slice):** `tulipbridge update` prints **data directory**, best-effort **public IPv4** (HTTPS reflectors), a **CGNAT / router WAN check** hint, and **listen ports** from `config.json`. Optional Cloudflare DDNS: set **`CLOUDFLARE_*`** env vars **or** **`tulipbridge cloudflare-write-config --token … --zone-id … --record-name …`** **or** copy **[docs/cloudflare.json.example](docs/cloudflare.json.example)** to **`etc/cloudflare.json`** (env overrides each field); **`update`** PATCHes the A record when IPv4 changes; cache **`etc/last_cloudflare_ip.txt`**. **Never commit API tokens.** After IP changes, run **`tulipbridge links`** or **`tulipbridge links --public-host …`** to refresh subscription files. Scheduled runs: **[docs/SCHEDULED_TASKS.md](docs/SCHEDULED_TASKS.md)** (cron / Task Scheduler / launchd / XML).

**Phase 5 (thin slice):** `tulipbridge status` prints **data directory**, **sing-box PID / running vs stale vs stopped**, **inbound ports** from `config.json`, a **localhost TCP probe** for VLESS, optional **Clash API `/memory` hint** when `init --enable-stats-api` was used, and **WAN / DNS vs subscription host**. **`tulipbridge restart`** stops sing-box if running and starts it again from existing **`etc/config.json`** (no key or subscribe regeneration — use **`init --force`** when you change ports/protocols). **`tulipbridge rotate-logs`** rotates **`logs/sing-box.log`** by size (`TULIPBRIDGE_LOG_MAX_BYTES`). **`tulipbridge alert`** notifies via **`TULIPBRIDGE_ALERT_WEBHOOK`** and/or **Telegram** (`TULIPBRIDGE_ALERT_TELEGRAM_BOT_TOKEN` + `TULIPBRIDGE_ALERT_TELEGRAM_CHAT_ID`) and/or **Bark** (`TULIPBRIDGE_ALERT_BARK_KEY`, or **`TULIPBRIDGE_ALERT_BARK_URL`** as an HTTPS base ending with the device key path) when the PID file is stale. UDP inbounds are listed but not probed (stdlib limitation). Scheduling: **[docs/SCHEDULED_TASKS.md](docs/SCHEDULED_TASKS.md)** (cron / launchd / Task Scheduler XML); templates under **`docs/`** (including **`windows-tulipbridge-alert.xml.example`**). Recovery patterns: **[docs/AUTO_RESTART.md](docs/AUTO_RESTART.md)**.

**More docs:** [docs/FAQ.md](docs/FAQ.md) (CGNAT, DDNS, subscriptions) · [docs/PREP_AND_CHINA_HANDOFF_ZH.md](docs/PREP_AND_CHINA_HANDOFF_ZH.md)（异步交接清单） · [docs/AUTO_RESTART.md](docs/AUTO_RESTART.md)（崩溃后重启思路）

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

**CI:** on every push/PR to `main`, [GitHub Actions](https://github.com/chasewang0718/tulipbridge/actions/workflows/ci.yml) runs **ruff** and **pytest** on **Ubuntu** (Python **3.10–3.13**), **Windows** (Python **3.11**), and **macOS** (Python **3.11**).

## Portable data directory

By default, binaries and config live under `~/.tulipbridge`. To keep everything in one folder (USB / self-contained repo copy):

- **`--portable`** — uses `./tulipbridge-data` under the **current working directory**. Put global options **before** the subcommand, e.g. `python -m tulipbridge --portable init` (not `init --portable`).
- **`--data-dir PATH`** — same idea but you choose the folder, e.g. `python -m tulipbridge --data-dir D:\tb-data init`.

Environment variable **`TULIPBRIDGE_HOME`** sets the data root when neither flag is used. **`--data-dir` / `--portable` override `TULIPBRIDGE_HOME`** for that process.

Moving to another PC: copy the data directory; on a different OS/architecture, run `init` again so sing-box can download the correct binary.

## Acceptance testing (Phase 1–2)

Manual checklist and pass criteria: [docs/ACCEPTANCE_PHASE1_2.md](docs/ACCEPTANCE_PHASE1_2.md). Automated checks: `pytest tests/ -q`.
