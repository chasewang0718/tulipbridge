# Restart sing-box after crashes (operator patterns)

TulipBridge’s Phase 5 thin slice includes **`tulipbridge alert`** when the **PID file is stale** — it **notifies** you but does **not** by itself start sing-box again. Use **`tulipbridge restart`** or your own scheduler.

## Preferred: `tulipbridge restart`

**`tulipbridge restart`** stops sing-box if it is running (or clears a stale PID file), then starts **`bin/sing-box`** with the existing **`etc/config.json`**. It does **not** regenerate keys or rewrite config; it does **not** refresh **`subscribe/`** (run **`tulipbridge links`** when your public host changes).

Use this after crashes or when **`status`** shows sing-box stopped, instead of re-running full **`init --force`** unless you changed ports or protocols.

## When to use `init --force` instead

Run **`tulipbridge init --force …`** with the **same flags** as your original **`init`** when you need to **change** listening ports, protocols, SNI, or TLS — that path rebuilds **`config.json`** and starts sing-box.

## Recommended approaches

### 1. Notification + restart

1. Schedule **`tulipbridge alert`** (see [SCHEDULED_TASKS.md](SCHEDULED_TASKS.md)).
2. When alerted, inspect **`logs/sing-box.log`**, then run **`tulipbridge restart`** (or call it from a watchdog script).

### 2. systemd (Linux): raw `sing-box` with `Restart=`

Advanced users run **`bin/sing-box`** directly:

```text
ExecStart=/path/to/datadir/bin/sing-box run -c /path/to/datadir/etc/config.json
Restart=on-failure
RestartSec=5
```

**Caveat:** TulipBridge’s **`sing-box.pid`** and **`tulipbridge status`** assume the process was started via **`tulipbridge init`** or **`tulipbridge restart`** (Python writes the PID file). If only systemd manages sing-box, **`status`** / **`alert`** may disagree until you align PID tracking.

### 3. Windows Task Scheduler

Periodic task: **`python -m tulipbridge --data-dir … restart`** (use sparingly — e.g. after boot or when paired with a guard that checks **`status`**). Pair with **`alert`** on a timer.

### 4. Pair with `alert`

Schedule **`alert`** more frequently than brute-force **`restart`** jobs so you get push/email/Bark **before** clients time out.

## Related

- Stale PID alerts: [FAQ.md](FAQ.md) — **Stale PID / webhook**
- Logs: **`tulipbridge rotate-logs`**
