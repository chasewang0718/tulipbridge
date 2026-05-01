# TulipBridge — Roadmap & Design Notes

翻墙合法性由使用者自负；本文仅描述技术架构。

---

## 设计概览

**目标**：在荷兰家宽上自动化部署 sing-box（VLESS-Reality / Hysteria 2 / TUIC v5），生成订阅/二维码，中国端 Shadowrocket 扫码即用。

**协议栈**：Reality（TCP 主力） → Hysteria 2（UDP 加速） → TUIC v5（UDP 备选）。

**硬性前提**：公网 IPv4、WAN 与 ifconfig.me 一致（非 CGNAT）、路由器端口映射。

**风险摘要**：国内 UDP 不稳以 Reality 兜底 · 动态 IP 用 DDNS · 单点以 UPS + 守护 + 通知缓解。

完整设计说明见下方各节（§A–§D）。

---

## 开发路线图

### Phase 0 — 项目骨架 ✅

> *已完成。*

- [x] `pyproject.toml`、`src/tulipbridge` 包结构
- [x] CLI 入口（`argparse`：`init` / `update` / `status` 占位）
- [x] `python -m tulipbridge` 可运行
- [x] dev 依赖（pytest、ruff）

---

### Phase 1 — sing-box 核心（`init` 可跑通单协议）✅

> 目标：`tulipbridge init` 能端到端跑起 **一条 VLESS-Reality 入站**。

- [x] **sing-box 二进制管理**
  - 从 GitHub Releases 按平台/架构下载对应预编译包
  - 解压到数据目录 `bin/`，记录版本
  - 版本检查 / 升级提示
- [x] **密钥生成**
  - Reality keypair（`sing-box generate reality-keypair`）
  - 用户 UUID（Python `uuid4`）
  - （Phase 2：Hy2/TUIC 使用 `sing-box generate tls-keypair` + `etc/tls/`）
- [x] **配置渲染**
  - Python `json` 构建 `config.json`（未使用 Jinja2）
  - **VLESS-Reality** 入站 + direct 出站；Phase 2 起可多入站
  - SNI 可配置（`--sni`）
- [x] **进程管理**
  - 启动 / 停止 sing-box 子进程；日志写入 `logs/sing-box.log`
  - （自动重启守护：Phase 5）
- [x] **数据目录约定**
  - `bin/`、`etc/`、`logs/`、`subscribe/`；另支持 `TULIPBRIDGE_HOME`、`--data-dir`、`--portable`

**交付标准**：在荷兰机器执行 `tulipbridge init`，sing-box 在指定 TCP 端口监听 VLESS-Reality。

---

### Phase 2 — 多协议入站 ✅

> 目标：配置文件同时承载三种协议，按优先级排列。

- [x] **Hysteria 2 入站**
  - 自签 TLS（`sing-box generate tls-keypair`，备选 `openssl`）；UDP 端口 `--hy2-port`
  - 密码自动生成并写入 `keys.json`
  - （ACME：后续可选）
- [x] **TUIC v5 入站**
  - 复用 VLESS UUID + `tuic_password`；UDP 端口 `--tuic-port`
- [x] **多入站合并**
  - `--vless` / `--no-vless`、`--hysteria2` / `--no-hysteria2`、`--tuic` / `--no-tuic`（默认全开）
  - `config.json` 一次写入全部启用的入站
  - 同协议栈内端口冲突检测（TCP 与 UDP 端口编号独立）
- [x] **`init` 参数**
  - 使用 CLI 开关与端口参数（非交互问答）；`--tls-sni` 对应 QUIC 证书 CN

**交付标准**：`tulipbridge init` 可一次生成并启动 **Reality + Hy2 + TUIC**（可按开关精简）。

---

### Phase 3 — 订阅、分享链接与二维码 ✅

> 目标：家人拿到链接或二维码即可在 Shadowrocket 中导入。

- [x] **分享链接生成**
  - `vless://`、`hysteria2://`、`tuic://` URI 格式
  - 兼容 Shadowrocket / sing-box 客户端解析
- [x] **订阅文件输出**
  - Base64 编码的多行链接（通用订阅格式），写入 `subscribe/subscription.txt`
  - 明文 `subscribe/uris-plain.txt` 便于核对
  - （可选后续：本地 HTTP 临时服务，用于局域网内取订阅）
- [x] **二维码生成**
  - 每条链接 → 终端 ASCII QR + `subscribe/qr-*.png`
  - `tulipbridge init --public-host …` 或 `tulipbridge links --public-host …` 生成
- [x] **Shadowrocket 兼容性矩阵**
  - 建议最低版本见 [docs/SHADOWROCKET.md](docs/SHADOWROCKET.md)（以 App Store 实际版本为准）

**交付标准**：提供公网 `HOST` 后，`init`/`links` 写入 `subscribe/` 并打印 QR；客户端按文档导入。

---

### Phase 4 — 网络与 DDNS

> 目标：`tulipbridge update` 能自动刷新 DNS 记录和订阅内容。

**薄切片（已交付）：** `update` 拉取公网 IPv4（HTTPS）、提示与路由器 WAN 对比（CGNAT / 双层路由）、列出 `config.json` 监听端口；可选 **Cloudflare A 记录**（环境变量 **或** `etc/cloudflare.json`，env 按字段覆盖）；定时任务见 **`docs/SCHEDULED_TASKS.md`**。

- [x] **网络前置检查（薄切片）**
  - [x] 公网 IPv4 查询（api.ipify.org / ifconfig.me 回退）
  - [x] CGNAT / 路由提示（人工对比路由器 WAN 与出口 IP）
  - [ ] 指定端口从外网可达性探测（设计说明：`docs/PORT_PROBE.md`；需外部探针，后续）
- [x] **Cloudflare DDNS（薄切片）**
  - [x] 环境变量：`CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ZONE_ID`、`CLOUDFLARE_RECORD_NAME`（FQDN）
  - [x] `update` 内 GET 记录 id + PATCH A 记录，TTL 120；缓存 `etc/last_cloudflare_ip.txt`
  - [x] **可选** `etc/cloudflare.json`（与 env 合并；示例 `docs/cloudflare.json.example`；**`tulipbridge cloudflare-write-config`** 非交互写入）
- [x] **`update` 命令（薄切片）**
  - [x] 展示当前出口 IPv4、配置中的监听端口、CGNAT 提示；提醒 `links --public-host` 刷新订阅
  - [x] 出口 IPv4 变化且配置 Cloudflare 环境变量时更新 DNS A 记录
  - [x] **cron / Task Scheduler**：见 `docs/SCHEDULED_TASKS.md`（可复制示例）
- [x] **订阅链接改用域名（薄切片）**
  - `init`/`links --public-host …` 将主机名写入 `etc/public_host.txt`
  - `tulipbridge links` 省略 `--public-host` 时：优先该文件，其次 `CLOUDFLARE_RECORD_NAME`（与 DDNS FQDN 一致即可）
  - 分享 URI 的 server 字段即为上述主机名（域名或 IP，由用户选择）

**交付标准（完整 Phase 4）：** IP 变化后 `tulipbridge update` 自动更新 Cloudflare DNS；订阅链接始终有效。**当前仓库：** DDNS 域名可持久化并作为默认 `links` 主机；仍可用手动 `links --public-host …` 覆盖。

---

### Phase 5 — 运维与监控（`status` + 守护）

> 目标：日常免登录、出问题能收到通知。

**薄切片（已交付）：** `status` 汇总数据目录、PID 文件与进程存活、配置中的入站端口；对 **VLESS TCP** 做本机 `127.0.0.1` 连接探测；**UDP** 仅列出端口（不做协议级探测）；**WAN / DNS**：订阅主机 A 记录 vs 出口 IPv4；可选 **Clash API `/memory`**（`init --enable-stats-api`）；**`restart`**（基于现有 `etc/config.json` 拉起 sing-box）；**`rotate-logs`** / **`alert`**（webhook / Telegram / Bark）见下文。

- [x] **`status` 命令（薄切片）**
  - [x] sing-box：无 PID / running / stale PID 文件
  - [x] 入站端口（从 `config.json`）；VLESS TCP 本机探测；UDP 配置说明
  - [x] 简要流量 / 内存提示（experimental `clash_api` + GET `/memory`，薄切片）
  - [x] 公网 IP 与 DNS 记录一致性校验（`etc/public_host.txt` / `CLOUDFLARE_RECORD_NAME` + DNS）
- [x] **服务化安装（文档示例）**
  - [x] Windows：**示例** Task Scheduler XML（`docs/windows-tulipbridge-update.xml.example`）；注册为 Windows Service 仍为后续
  - [x] Linux：**示例** systemd unit（`docs/tulipbridge.service.example`）；交互式生成器后续
  - [x] macOS：**示例** launchd plist（`docs/com.tulipbridge.update.plist.example`）；交互式生成器后续
- [x] **掉线通知（薄切片）**
  - [x] Webhook：`TULIPBRIDGE_ALERT_WEBHOOK` + `tulipbridge alert`（stale PID）
  - [x] Telegram：`TULIPBRIDGE_ALERT_TELEGRAM_BOT_TOKEN` + `TULIPBRIDGE_ALERT_TELEGRAM_CHAT_ID`（可与 webhook 同时配置）
  - [x] Bark（薄切片：`TULIPBRIDGE_ALERT_BARK_KEY` / `TULIPBRIDGE_ALERT_BARK_URL` + `tulipbridge alert` GET）
- [x] **日志轮转（薄切片）**
  - [x] `tulipbridge rotate-logs`：按大小轮转 `logs/sing-box.log`（`TULIPBRIDGE_LOG_MAX_BYTES`）
- [x] **进程重启（薄切片）**
  - [x] `tulipbridge restart`：停止现有进程（若有）并以现有 `etc/config.json` 启动 sing-box（不改密钥与订阅；详见 `docs/AUTO_RESTART.md`）

**交付标准**：`tulipbridge status` 输出一目了然的健康面板；进程崩溃可通过 **`tulipbridge alert`** 获知，并可 **`tulipbridge restart`** 或 **`init --force`**（改配置时）恢复进程；长期无人值守的 watchdog 仍由 systemd / 计划任务等承担（`docs/AUTO_RESTART.md`）。

---

### Phase 6 — 质量与文档

> 目标：项目可交付、可维护。

- [x] **测试**
  - [x] 单元测试（密钥生成、`export_share_bundle`、配置解析等；见 `tests/test_keygen.py` 等）
  - [x] 集成测试（薄切片：`tests/test_init_integration.py`，mock `ensure_singbox` / `start_singbox`）
  - [x] CI（GitHub Actions：`ruff` + `pytest`，Ubuntu / Windows / macOS — 见 `.github/workflows/ci.yml`）
- [x] **跨平台验证**
  - [x] Windows：GitHub Actions **windows-latest** + Python 3.11（CI）
  - [x] Linux：GitHub Actions **ubuntu-latest** 矩阵（CI）
  - [x] macOS：**GitHub Actions macos-latest** + Python 3.11（CI）；本地亦可 `pip install -e '.[dev]'` + `pytest`
- [x] **用户文档**
  - [x] 端到端快速开始指南（薄切片：`docs/QUICKSTART.md`）
  - [x] 路由器端口映射说明（薄切片：`docs/ROUTER_NAT.md`；配图截图可为后续）
  - [x] Shadowrocket 导入步骤（薄切片：`docs/SHADOWROCKET_IMPORT.md`；截图可按 App 版本后续补充）
  - [x] 异步交接 / 中方最后联调（`docs/PREP_AND_CHINA_HANDOFF_ZH.md`）
  - [x] 常见问题 / 故障排查（薄切片：`docs/FAQ.md`）
- [x] **安全审查**
  - [x] 文档摘要（薄切片：`docs/SECURITY.md` — 密钥、`cloudflare.json`、订阅与 webhook）
  - [x] API token / 密钥存放：推荐环境变量与文件权限；加密配置库为后续可选（见 `docs/SECURITY.md`「Credentials」）
  - [x] 订阅链接防泄漏建议（见 SECURITY / FAQ）

**交付标准**：CI 绿灯，README 足够新用户从零开始跑通全流程。

---

## 附录

### A. 协议与角色分工

| 优先级 | 协议 | 传输 | 作用 |
|--------|------|------|------|
| **主力** | VLESS-Reality | TCP 443 | TCP 生存性最好，日常常驻 |
| **加速** | Hysteria 2 | UDP/QUIC | 延迟与带宽友好；部分运营商 UDP 不友好 |
| **备选** | TUIC v5 | UDP/QUIC | 比 Hy2 温和，轻度 QoS 时更稳 |

以 **Reality 为主、UDP 为辅**，客户端可在订阅里排序或手动切换。

### B. 运行环境

- **服务端**：Windows / macOS / Linux，Python 3.10+，公网 IPv4 + 路由器端口映射，DDNS。
- **客户端**：iOS/macOS Shadowrocket 或 sing-box 官方客户端。

### C. 网络前提

1. 路由器 WAN IPv4 = `ifconfig.me` → 非 CGNAT，直连可行。
2. WAN 为 `100.64.x.x` 或不一致 → CGNAT，需联系 ISP 或改架构。
3. Cloudflare Tunnel 仅适用于无公网的 TCP 场景，不替代 UDP 端口映射。

### D. 风险与对策

| 风险 | 对策 |
|------|------|
| 国内 UDP 差 | Reality 兜底 |
| 动态 IP | Cloudflare DDNS + 短 TTL |
| 单点故障 | UPS + 守护 + 通知 |
| Reality SNI 被针对 | 跟进社区实践更新伪装目标 |
| Shadowrocket 兼容 | 锁定最低版本写入文档 |
