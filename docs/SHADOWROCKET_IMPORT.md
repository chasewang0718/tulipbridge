# Import TulipBridge into Shadowrocket (step by step)

This guide assumes you already ran `tulipbridge init` (or `tulipbridge links`) with a correct **`--public-host`** and have files under **`subscribe/`** on the server. For **minimum app versions** and URI compatibility, read [SHADOWROCKET.md](SHADOWROCKET.md) first.

> **Screenshots:** UI labels change with App Store updates. This document is **text-only**; you can add versioned screenshots later without changing the flow below.

## Why PNG QR, not the terminal

On **Windows**, the **ASCII QR** printed in the console is often hard for phone cameras to read. **Prefer the PNG files** written to `subscribe/qr-*.png` (transfer via AirDrop, cloud drive, or send the file to the phone).

## Method A — Scan a QR (recommended)

1. Copy **`subscribe/qr-vless-reality.png`** (and/or hy2 / tuic) to your iPhone, or open the share folder on a machine the phone can access.
2. Open **Shadowrocket** on iOS.
3. Use the in-app **scan** / **+** flow to **scan the QR image** (exact menu names may vary by version; look for scan or add-from-QR).
4. Confirm the new node appears; test connectivity (same WiFi or cellular per your plan).

## Method B — Import one URI from clipboard

1. On the server, open **`subscribe/uris-plain.txt`** and copy **one full line** (a `vless://`, `hysteria2://`, or `tuic://` URI).
2. On the iPhone, copy that line to the clipboard.
3. Open Shadowrocket and use **import from clipboard** (wording may vary: e.g. “从剪贴板导入”).
4. Save the node and test.

## Method C — Subscription (Base64 bundle)

1. TulipBridge writes **`subscribe/subscription.txt`** (Base64-encoded list of URIs). Some clients expect a **remote HTTPS URL** to that content; Shadowrocket’s UI for “subscribe URL” / remote profile changes over time—use the **current** Shadowrocket docs or in-app help.
2. Alternatively import **`subscribe/subscription.txt`** or **`uris-plain.txt`** via **Files / iCloud** if the app version supports local file import.

## After import fails

- Re-run **`tulipbridge links`** with the correct **`--public-host`** (or rely on `etc/public_host.txt` / `CLOUDFLARE_RECORD_NAME`).
- Upgrade Shadowrocket per the table in [SHADOWROCKET.md](SHADOWROCKET.md).
- For Hy2/TUIC, ensure **insecure / SNI** matches server TLS — see [SHADOWROCKET.md](SHADOWROCKET.md#self-signed-tls-hysteria-2--tuic).

## Related

- China-side testing timeline: [PREP_AND_CHINA_HANDOFF_ZH.md](PREP_AND_CHINA_HANDOFF_ZH.md)
