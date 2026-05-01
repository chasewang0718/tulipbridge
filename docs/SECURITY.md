# TulipBridge — security notes

This document summarizes how sensitive data is handled and how to reduce accidental leakage. It is **not** a formal audit.

## Keys and certificates

- **`etc/keys.json`** holds UUIDs, Reality keys, QUIC passwords, and optional **`clash_api_secret`** when stats API is enabled.
- On Unix, TulipBridge attempts **`chmod 600`** on `keys.json` and **`etc/cloudflare.json`** after writes.
- **Back up** the data directory securely; treat backups like production secrets.

## Credentials (tokens and secrets)

This project **does not ship an encrypted secrets vault**. Recommended practice:

1. **Prefer environment variables** for **`CLOUDFLARE_*`**, **`TULIPBRIDGE_ALERT_*`**, and Telegram/Bark tokens — inject via **systemd** `Environment=` / `EnvironmentFile=`, **cron** `env` or a root-owned **`chmod 600`** script that exports vars, or **Task Scheduler** user env / wrapper batch file (Windows env UI is limited; wrapper scripts are reliable).
2. **Files**: **`etc/cloudflare.json`** and **`etc/keys.json`** — on Unix, restrict with **`chmod 600`** (TulipBridge sets this after writes when possible). Never commit them or paste into tickets/chat.
3. **Encrypted at-rest storage** (Vault, OS keychain integration, etc.) is **out of scope** for this CLI; advanced users can wrap TulipBridge with their own secret distribution.

More operational detail: [FAQ.md](FAQ.md)（Cloudflare token、`chmod`）.

## Cloudflare and webhooks

- **`CLOUDFLARE_*`** environment variables and **`etc/cloudflare.json`** contain API tokens. Never commit them; prefer OS secret stores or systemd **`Environment=`** / Task Scheduler environment.
- **`TULIPBRIDGE_ALERT_WEBHOOK`**: use an HTTPS URL you control. The alert payload contains **hostname**, **sing_box state**, and **UTC time** only — no subscription material.
- **Telegram** (optional, same **`tulipbridge alert`** stale-PID condition): **`TULIPBRIDGE_ALERT_TELEGRAM_BOT_TOKEN`** and **`TULIPBRIDGE_ALERT_TELEGRAM_CHAT_ID`**. Treat the bot token like a password; never commit it. You may use Webhook and Telegram together.
- **Bark** (optional, same condition): **`TULIPBRIDGE_ALERT_BARK_KEY`** builds a GET to `https://api.day.app/…` with URL-encoded title/body (hostname/time only — no subscription material). **`TULIPBRIDGE_ALERT_BARK_URL`** overrides the base URL (HTTPS prefix ending with your device key path, for self-hosted Bark). Treat the key like a webhook secret.

## Subscribe directory

- **`subscribe/subscription.txt`**, **`uris-plain.txt`**, and QR PNGs encode live node parameters. Treat like passwords when copying off the server.

## Stats API (optional)

- **`--enable-stats-api`** binds sing-box **Clash API** on **`127.0.0.1`** only by default. A random secret is stored in `keys.json`. Do not expose the controller port on WAN without firewall rules you understand.

## Reporting issues

If you find a vulnerability, disclose responsibly (maintainer contact via your usual GitHub channel).
