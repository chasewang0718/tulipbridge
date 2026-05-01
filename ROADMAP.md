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

**薄切片（已交付）：** `update` 拉取公网 IPv4（HTTPS）、提示与路由器 WAN 对比（CGNAT / 双层路由）、列出 `config.json` 监听端口；Cloudflare 与自动 DNS 仍在下文。

- [x] **网络前置检查（薄切片）**
  - [x] 公网 IPv4 查询（api.ipify.org / ifconfig.me 回退）
  - [x] CGNAT / 路由提示（人工对比路由器 WAN 与出口 IP）
  - [ ] 指定端口从外网可达性探测（需外部探针或路由器配合，后续）
- [ ] **Cloudflare DDNS**
  - 通过 Cloudflare API 更新 A 记录
  - 短 TTL（60–120s）
  - 配置存储：zone id、API token、域名（首次 init 时写入）
- [x] **`update` 命令（薄切片）**
  - [x] 展示当前出口 IPv4、配置中的监听端口、CGNAT 提示；提醒 `links --public-host` 刷新订阅
  - [ ] 检测公网 IP 变化 → 更新 DNS（依赖 Cloudflare 实现）
  - [ ] 可接入 cron / Task Scheduler 定时执行
- [ ] **订阅链接改用域名**
  - 分享链接中的 server 字段使用 DDNS 域名而非 IP

**交付标准（完整 Phase 4）：** IP 变化后 `tulipbridge update` 自动更新 Cloudflare DNS；订阅链接始终有效。**当前仓库：** 可先用手动 `links` + `update` 自查 IP/端口。

---

### Phase 5 — 运维与监控（`status` + 守护）

> 目标：日常免登录、出问题能收到通知。

**薄切片（已交付）：** `status` 汇总数据目录、PID 文件与进程存活、配置中的入站端口；对 **VLESS TCP** 做本机 `127.0.0.1` 连接探测；**UDP** 仅列出端口（不做协议级探测）。流量统计 / API / 公网 DNS 一致性仍为下文。

- [x] **`status` 命令（薄切片）**
  - [x] sing-box：无 PID / running / stale PID 文件
  - [x] 入站端口（从 `config.json`）；VLESS TCP 本机探测；UDP 配置说明
  - [ ] 简要流量统计（若 sing-box API 可用）
  - [ ] 公网 IP 与 DNS 记录一致性校验（可与 `update` 衔接）
- [ ] **服务化安装**
  - Windows：注册为 Windows Service 或生成 Task Scheduler XML
  - Linux：生成 systemd unit 文件
  - macOS：生成 launchd plist
- [ ] **掉线通知（可选）**
  - Telegram Bot / Bark / Webhook
  - 检测 sing-box 意外退出或端口不可达时发送通知
- [ ] **日志轮转**
  - 按大小或天数自动轮转日志文件

**交付标准**：`tulipbridge status` 输出一目了然的健康面板；sing-box 崩溃可自动重启并发通知。

---

### Phase 6 — 质量与文档

> 目标：项目可交付、可维护。

- [ ] **测试**
  - 单元测试（密钥生成、配置渲染、链接格式）
  - 集成测试（mock sing-box 二进制的 init 流程）
  - [x] CI（GitHub Actions：`ruff` + `pytest`，Ubuntu，Python 3.10–3.13）
- [ ] **跨平台验证**
  - [x] Windows：GitHub Actions **windows-latest** + Python 3.11（CI）
  - [x] Linux：GitHub Actions **ubuntu-latest** 矩阵（CI）
  - macOS（可选）
- [ ] **用户文档**
  - 端到端快速开始指南
  - 路由器端口映射图文说明
  - Shadowrocket 导入步骤（截图）
  - [x] 异步交接 / 中方最后联调（`docs/PREP_AND_CHINA_HANDOFF_ZH.md`）
  - 常见问题 / 故障排查
- [ ] **安全审查**
  - 密钥文件权限（600 / 仅当前用户可读）
  - API token 存储方式（环境变量 / 加密配置）
  - 订阅链接防泄漏建议

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
