# TulipBridge — FAQ / troubleshooting

## Port forwarding on the router

You must forward **WAN → LAN** for the TCP/UDP ports shown by **`tulipbridge status`** (same numbers). See [ROUTER_NAT.md](ROUTER_NAT.md).

## CGNAT / “router WAN ≠ outbound IP”

If `tulipbridge update` shows a public IPv4 but your router admin page shows a different WAN address (often `100.64.x.x` or another private range), you may be behind **carrier-grade NAT** or **double NAT**. Clients on the internet cannot reach port forwards on your home router until your ISP gives you a routable WAN IPv4 or you change architecture (e.g. VPS relay — outside this project’s scope).

## Dynamic IP and DDNS

When your ISP changes your IPv4, update DNS (Cloudflare DDNS via `update` when configured) and regenerate subscriptions so clients see the correct host:

```bash
tulipbridge update
tulipbridge links
```

See [SCHEDULED_TASKS.md](SCHEDULED_TASKS.md) for cron / Task Scheduler examples.

## “Mismatch” in `tulipbridge status` (WAN / DNS)

The status panel compares **your current outbound IPv4** with **DNS A records** for your subscription hostname (`etc/public_host.txt` or `CLOUDFLARE_RECORD_NAME`). After updating DNS, wait for **TTL** (and Cloudflare propagation), then run `links` again. If it stays wrong, confirm the A record in the Cloudflare dashboard.

## Cloudflare token / `etc/cloudflare.json`

You can set **`CLOUDFLARE_API_TOKEN`**, **`CLOUDFLARE_ZONE_ID`**, **`CLOUDFLARE_RECORD_NAME`** in the environment, run **`tulipbridge cloudflare-write-config --token … --zone-id … --record-name …`** (writes `etc/cloudflare.json` with safe permissions on Unix), or copy from [cloudflare.json.example](cloudflare.json.example). Per-field values in the environment override the file.

**Never commit tokens.** On Unix, restrict the file (`chmod 600 etc/cloudflare.json`). Prefer environment injection from your scheduler or systemd `Environment=` when possible.

For a concise policy on **all** secrets (alerts, Bark, subscribe files): see [SECURITY.md](SECURITY.md) — **Credentials**.

## Log growth (`logs/sing-box.log`)

Run **`tulipbridge rotate-logs`** on a schedule if logs grow large (see [SCHEDULED_TASKS.md](SCHEDULED_TASKS.md)). Env **`TULIPBRIDGE_LOG_MAX_BYTES`** sets the threshold.

## Stale PID / webhook (`tulipbridge alert`)

If sing-box crashed but **`sing-box.pid`** still exists, configure at least one channel:

- **`TULIPBRIDGE_ALERT_WEBHOOK`**: HTTPS URL; **`tulipbridge alert`** POSTs JSON (hostname, state, UTC time).
- **Telegram**: **`TULIPBRIDGE_ALERT_TELEGRAM_BOT_TOKEN`** + **`TULIPBRIDGE_ALERT_TELEGRAM_CHAT_ID`** (same **`alert`** command).
- **Bark**: **`TULIPBRIDGE_ALERT_BARK_KEY`** (official server) or **`TULIPBRIDGE_ALERT_BARK_URL`** (full HTTPS base including device key path, e.g. self-hosted); **`alert`** issues a short GET with encoded title/body.

Any combination can be set. No subscription secrets are included.

## Restart vs `init --force`

- **`tulipbridge restart`**: stop sing-box if running, then start from the existing **`etc/config.json`**. Does not regenerate keys or **`subscribe/`**. Use after a crash or manual stop when settings are unchanged.
- **`tulipbridge init --force …`**: rewrite **`config.json`** from current CLI flags and start sing-box — use when you change ports, protocols, or TLS/SNI. Keep a saved command line or script.

See [AUTO_RESTART.md](AUTO_RESTART.md).

## Subscription files not updating

Share links are written under **`subscribe/`** by `init --public-host …` or `tulipbridge links`. They do **not** auto-update when only sing-box config changes — run **`tulipbridge links`** after hostname or IP-related changes.

## Shadowrocket import issues

See [SHADOWROCKET.md](SHADOWROCKET.md). Prefer **PNG QR** from `subscribe/qr-*.png` on Windows terminals that distort ASCII QR.
