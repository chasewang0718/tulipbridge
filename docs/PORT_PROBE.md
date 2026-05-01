# External port reachability (future / external dependency)

[ROADMAP](../ROADMAP.md) Phase 4 lists **「指定端口从外网可达性探测」**. TulipBridge does **not** include a hosted public probe service.

## Why it is deferred

- A machine behind NAT cannot reliably verify **WAN → DNAT → listen port** using only local sockets.
- Meaningful checks require **another host on the Internet** (VPS, cloud function, or a cooperative peer) that completes TCP connect or UDP echo toward your public IP and mapped ports.

## Practical approaches

1. **Manual**: From mobile data or [icanhazip](https://icanhazip.com)-class checks, use a port-scan tool or `curl`/`nc` from a VPS you control.
2. **Router UI**: Confirm port forwarding rules match TulipBridge listen ports from `tulipbridge status`.
3. **Future CLI hook** (not implemented): `--probe-url https://your-vps.example/probe?port=443` returning reachability JSON — user-operated endpoint only.

Until a probe protocol is standardized, see [FAQ.md](FAQ.md) for CGNAT and forwarding hints. Async handoff checklist: [PREP_AND_CHINA_HANDOFF_ZH.md](PREP_AND_CHINA_HANDOFF_ZH.md)（推荐外网抽查端口）。

**Step-by-step (Chinese, beginner-friendly):** [PORT_PROBE_STEP_BY_STEP_ZH.md](PORT_PROBE_STEP_BY_STEP_ZH.md).
