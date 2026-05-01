# TulipBridge quick start

Minimal path from clone to a running sing-box home server and phone-ready subscription files.

## 1. Install (editable)

```bash
cd tulipbridge
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows
pip install -e .
```

## 2. First-time setup

Use a fixed data directory (recommended for servers):

```bash
python -m tulipbridge --data-dir ~/.tulipbridge init --public-host YOUR_WAN_IP_OR_DOMAIN
```

Or portable mode (folder next to cwd):

```bash
python -m tulipbridge --portable init --public-host YOUR_WAN_IP_OR_DOMAIN
```

- **`--public-host`**: Address clients will use (LAN IP for WiFi testing, public IP or DDNS hostname for real use).
- Optional **`--enable-stats-api`**: Enables sing-box Clash API on `127.0.0.1` so `tulipbridge status` can show a `/memory` hint.

Windows step-by-step (Chinese): [HANDS_ON_WINDOWS_ZH.md](HANDS_ON_WINDOWS_ZH.md).

## 3. Refresh subscription after IP or DNS changes

```bash
python -m tulipbridge --data-dir ~/.tulipbridge update
python -m tulipbridge --data-dir ~/.tulipbridge links
```

Cloudflare DDNS: set env vars or run `cloudflare-write-config`, then schedule `update` — see [SCHEDULED_TASKS.md](SCHEDULED_TASKS.md).

## 4. Health check

```bash
python -m tulipbridge --data-dir ~/.tulipbridge status
```

If sing-box exited but config is unchanged, you can **`restart`** (same data dir):

```bash
python -m tulipbridge --data-dir ~/.tulipbridge restart
```

See [AUTO_RESTART.md](AUTO_RESTART.md) vs **`init --force`** when you change ports or protocols.

## 5. Router port forwarding (required for WAN access)

Open the same **TCP/UDP** ports on your router to this machine’s **LAN IP**: [ROUTER_NAT.md](ROUTER_NAT.md).

## 6. Import on iOS (Shadowrocket)

Follow [SHADOWROCKET_IMPORT.md](SHADOWROCKET_IMPORT.md) (QR PNG, clipboard, subscription). Version hints: [SHADOWROCKET.md](SHADOWROCKET.md). Prefer **`subscribe/qr-*.png`** over terminal ASCII QR on Windows.

## FAQ / security / China-side handoff

- [FAQ.md](FAQ.md)
- [SECURITY.md](SECURITY.md)
- 与中方面前最后一跳异步联调：[PREP_AND_CHINA_HANDOFF_ZH.md](PREP_AND_CHINA_HANDOFF_ZH.md)
