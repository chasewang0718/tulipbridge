# Scheduled `update` / `links` / `alert`

Use **cron** (Linux/macOS) or **Task Scheduler** (Windows) so `tulipbridge update` runs periodically (DDNS), you refresh subscriptions after IP changes, and optionally **`tulipbridge alert`** runs for stale-PID notifications. **`tulipbridge restart`** is for one-shot or scripted process recovery — see [AUTO_RESTART.md](AUTO_RESTART.md).

Adjust paths: Python interpreter (venv), data directory (`TULIPBRIDGE_HOME`, `--data-dir`, or `--portable`), and shell.

## macOS — launchd (recommended)

Use a **LaunchAgent** instead of cron for reliable intervals when logged in.

1. Copy **[com.tulipbridge.update.plist.example](com.tulipbridge.update.plist.example)** to `~/Library/LaunchAgents/com.tulipbridge.update.plist`.
2. Edit `ProgramArguments`, `EnvironmentVariables`, and log paths (create `logs/` under your data directory if needed).
3. Load and enable:

```bash
launchctl load -w ~/Library/LaunchAgents/com.tulipbridge.update.plist
```

4. Check status:

```bash
launchctl print gui/$(id -u)/com.tulipbridge.update
```

Unload with `launchctl unload ~/Library/LaunchAgents/com.tulipbridge.update.plist`.

You can add a second plist for daily `tulipbridge links` using `StartCalendarInterval` (see `man launchd.plist`).

## Linux — cron

Example: every 15 minutes run `update`; daily regenerate subscription files if your host is already stored (`etc/public_host.txt` or `CLOUDFLARE_RECORD_NAME`).

```cron
*/15 * * * * /home/you/.local/bin/tulipbridge update >> /home/you/.tulipbridge/logs/update.log 2>&1
0 6 * * * /home/you/.local/bin/tulipbridge links >> /home/you/.tulipbridge/logs/links.log 2>&1
```

If `tulipbridge` is not on `PATH`, use the full path to your venv:

`/home/you/tulipbridge/.venv/bin/tulipbridge`.

Portable mode example (paths relative to working directory):

```cron
*/15 * * * * cd /opt/tulipbridge && /opt/tulipbridge/.venv/bin/python -m tulipbridge --portable update
```

## Windows — Task Scheduler or `schtasks`

Create tasks that run **when you are logged on** (or as a service account that has access to the data directory).

### Import XML (recommended for repeatable edits)

Use **[windows-tulipbridge-update.xml.example](windows-tulipbridge-update.xml.example)**:

1. Copy the file, edit `<Command>`, `<Arguments>`, `<WorkingDirectory>` (and trigger times if needed).
2. Open **Task Scheduler** → **Create Task** is optional; instead use **Import Task…** and pick your edited XML.
3. Or from **elevated cmd** (paths adjusted):

```bat
schtasks /Create /TN "TulipBridgeUpdate" /XML D:\tb-data\windows-tulipbridge-update.xml /F
```

### One-off `schtasks` (no XML file)

Run elevated **cmd** and edit paths:

```bat
schtasks /Create /TN "TulipBridgeUpdate" /TR "C:\path\to\.venv\Scripts\python.exe -m tulipbridge --data-dir D:\tb-data update" /SC MINUTE /MO 15
schtasks /Create /TN "TulipBridgeLinks" /TR "C:\path\to\.venv\Scripts\python.exe -m tulipbridge --data-dir D:\tb-data links" /SC DAILY /ST 06:00
```

Or use **Task Scheduler** GUI: Action = **Start a program**, Program = `python.exe`, Arguments = `-m tulipbridge --data-dir D:\tb-data update`, Start in = project folder.

Set **Environment** on Windows if you rely on `CLOUDFLARE_*` without `etc/cloudflare.json`.

## `tulipbridge alert` (stale PID)

Run **`alert`** on a interval so you notice crashes when **`sing-box.pid`** is left behind. Configure **at least one** channel via environment variables (same vars as in [SECURITY.md](SECURITY.md)):

| Variable | Role |
|----------|------|
| **`TULIPBRIDGE_ALERT_WEBHOOK`** | HTTPS POST JSON |
| **`TULIPBRIDGE_ALERT_TELEGRAM_BOT_TOKEN`** + **`TULIPBRIDGE_ALERT_TELEGRAM_CHAT_ID`** | Telegram |
| **`TULIPBRIDGE_ALERT_BARK_KEY`** or **`TULIPBRIDGE_ALERT_BARK_URL`** | Bark GET |

Inject these into the task environment (Windows **Task Scheduler** → task → **Actions** / **General** → environment is limited; prefer wrapping script that sets env or systemd **`Environment=`**).

### Linux — cron

Example every **10** minutes (adjust `--data-dir` / `--portable`):

```cron
*/10 * * * * TULIPBRIDGE_ALERT_WEBHOOK=https://example.com/hook /home/you/tulipbridge/.venv/bin/tulipbridge --data-dir /home/you/.tulipbridge alert >> /home/you/.tulipbridge/logs/alert.log 2>&1
```

Or use a **`cron`** line that **`source`**s a file exporting secrets (permissions **`chmod 600`**).

### Linux — systemd timer (alternative to cron)

Copy **[tulipbridge-alert.service.example](tulipbridge-alert.service.example)** and **[tulipbridge-alert.timer.example](tulipbridge-alert.timer.example)** to `~/.config/systemd/user/`, adjust paths and **`Environment=`**, then:

```bash
systemctl --user daemon-reload
systemctl --user enable --now tulipbridge-alert.timer
```

### Windows — Task Scheduler

#### Import XML (repeatable)

Use **[windows-tulipbridge-alert.xml.example](windows-tulipbridge-alert.xml.example)** (same import flow as **`windows-tulipbridge-update.xml.example`**).

#### One-off `schtasks`

Elevated **cmd** (edit paths and optionally split webhook into **System** environment or a wrapper `.bat`):

```bat
schtasks /Create /TN "TulipBridgeAlert" /TR "C:\path\to\.venv\Scripts\python.exe -m tulipbridge --data-dir D:\tb-data alert" /SC MINUTE /MO 10
```

Set **`TULIPBRIDGE_ALERT_*`** for the task: **Task Scheduler** → task → **Actions** → **Edit** → prepend env is awkward on Windows; recommended: use **batch file** that **`set`**s vars then runs `python -m tulipbridge … alert`.

### macOS — launchd

Add a second plist (copy [com.tulipbridge.update.plist.example](com.tulipbridge.update.plist.example)), change **`ProgramArguments`** to end with **`alert`**, set **`StartInterval`** (seconds) e.g. **600**, and put **`EnvironmentVariables`** dict with your **`TULIPBRIDGE_ALERT_*`** keys.

## Log file size (`rotate-logs`)

`sing-box` appends to `logs/sing-box.log`. Run periodically:

```bash
tulipbridge rotate-logs
```

Default max size **10 MiB** before rotating to `sing-box.log.1`. Override with **`TULIPBRIDGE_LOG_MAX_BYTES`** (bytes, minimum 1024 when read from env internally — see source).

## Notes

- Crash recovery: **`tulipbridge restart`** (see [AUTO_RESTART.md](AUTO_RESTART.md)); pair **`alert`** with timers or watchdog scripts for unattended hosts.
- `update` exits 0 even when reflectors fail; check logs if DDNS never updates.
- After WAN IP changes, clients need refreshed subscription files (`links`).
- See [tulipbridge.service.example](tulipbridge.service.example) for **systemd** `update` (Linux).
- See [tulipbridge-alert.service.example](tulipbridge-alert.service.example) + [tulipbridge-alert.timer.example](tulipbridge-alert.timer.example) for **systemd** `alert`.
- See [com.tulipbridge.update.plist.example](com.tulipbridge.update.plist.example) for **macOS launchd**.
- See [windows-tulipbridge-update.xml.example](windows-tulipbridge-update.xml.example) and [windows-tulipbridge-alert.xml.example](windows-tulipbridge-alert.xml.example) for **Windows Task Scheduler XML** import.
