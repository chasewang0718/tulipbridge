# Shadowrocket compatibility (TulipBridge)

Use **Shadowrocket** or **sing-box** on iOS/macOS to import TulipBridge share links or the Base64 subscription file.

## Minimum app versions (guidance)

Client URI dialects change between releases. Treat the versions below as **practical lower bounds** for the share formats TulipBridge generates; **always confirm against the App Store build you actually install**.

| Feature | Suggested minimum Shadowrocket | Notes |
|--------|--------------------------------|--------|
| VLESS + Reality (`flow=xtls-rprx-vision`) | **2.2.50+** (guidance) | Match sing-box / Xray Reality parameter names (`pbk`, `sid`, `sni`). |
| Hysteria 2 | **2.2.40+** (guidance) | `hysteria2://` with `insecure` + `sni` for self-signed TLS. |
| TUIC v5 | **2.2.40+** (guidance) | `tuic://` with UUID/password and QUIC-related query params. |

If import fails after an update, re-export links with `tulipbridge links --public-host …` and try again.

## Import methods

Step-by-step (Shadowrocket UI): [SHADOWROCKET_IMPORT.md](SHADOWROCKET_IMPORT.md).

1. **QR code** — Prefer scanning **`subscribe/qr-*.png`** on disk (terminal ASCII QR can be hard to scan on some Windows fonts).
2. **Clipboard** — Copy a single line from `subscribe/uris-plain.txt` and use Shadowrocket’s “Import from clipboard”.
3. **Subscription URL / Base64** — Many clients accept a **Base64-encoded list of URIs** (one URI per line before encoding). TulipBridge writes this to **`subscribe/subscription.txt`**. Import depends on the client: some expect a remote HTTPS URL, others let you paste Base64 or import the file via iCloud/files — follow Shadowrocket’s current UI for “subscribe” / “remote profile”.

## Self-signed TLS (Hysteria 2 / TUIC)

Share URIs include **`insecure` / `allow_insecure`** and **`sni`** aligned with your server’s `--tls-sni` and `keys.json`. Clients must allow insecure verification or pin the server certificate until you use a publicly trusted cert.
