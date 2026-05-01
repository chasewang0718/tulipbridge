# Phase 1 / Phase 2 详细验收计划

以下为**自测/交付验收**用的步骤与判据；不涉及 Phase 3（分享链接/二维码）。默认数据目录为 **`%USERPROFILE%\.tulipbridge`**（Linux/macOS 为 `~/.tulipbridge`），便携模式见 §0。

---

## 验收前环境（共用）

| 项 | 要求 |
|----|------|
| Python | 3.10+，`pip install -e .` 或 `pip install -e ".[dev]"` 成功 |
| 网络 | 首次 `init` 需能访问 GitHub API / Releases（下载 sing-box） |
| 权限 | Windows 监听 **443** 可能需要管理员权限；验收可用 **`--port 8443`** 等非特权端口 |
| 目录 | 验收前可备份或清空测试用数据目录，避免旧 PID/密钥干扰 |

**退出码：** 每次命令后执行 `echo $LASTEXITCODE`（PowerShell）或 `echo %ERRORLEVEL%`（CMD）；成功应为 **`0`**。勿将 stdout **管道截断**（如 `Select-Object -First 15`），否则易出现**假非零退出码**。

---

## §0 便携与数据根（跨 Phase，建议至少验 1 条）

| ID | 步骤 | 期望结果 |
|----|------|----------|
| P0-1 | `python -m tulipbridge --help` | 出现 `--data-dir`、`--portable` |
| P0-2 | `python -m tulipbridge --portable init --no-hysteria2 --no-tuic --port 8443 --force`（在工作目录执行） | 数据写在 **`.\tulipbridge-data\`** 下（含 `bin`、`etc`） |
| P0-3 | 设置环境变量 `TULIPBRIDGE_HOME` 指向自定义路径后执行 `init`（不设 `--data-dir`） | 文件落在该路径下 |

---

## Phase 1 验收（目标：仅 **VLESS-Reality**，无 Hy2/TUIC）

### A. CLI 与安装

| ID | 步骤 | 期望结果 |
|----|------|----------|
| 1-A1 | `python -m tulipbridge --version` | 打印 tulipbridge 版本 |
| 1-A2 | `python -m tulipbridge init --help` | 含 `--port`、`--sni`、`--singbox-version`、`--force`；含 **`--no-hysteria2`、`--no-tuic`** 等协议开关 |
| 1-A3 | `python -m ruff check src/tulipbridge`（dev） | 无报错 |

### B. 首次 init（仅 VLESS）

| ID | 步骤 | 期望结果 |
|----|------|----------|
| 1-B1 | `python -m tulipbridge init --no-hysteria2 --no-tuic --port 8443 --force` | 流程约 **[1/7]…[7/7]** 完成；终端打印 **PID**、**TCP 端口**、**UUID**、**Reality 公钥**、**short_id**、**Reality SNI**、**config 路径** |
| 1-B2 | 同上命令后立即查退出码 | **`0`** |

### C. 磁盘产物（数据根下）

| ID | 路径（相对数据根） | 期望 |
|----|---------------------|------|
| 1-C1 | `bin/sing-box.exe`（Windows）或 `bin/sing-box` | 存在且为可执行文件 |
| 1-C2 | `bin/VERSION` | 有版本号文本 |
| 1-C3 | `etc/keys.json` | 含 `uuid`、`reality_private_key`、`reality_public_key`、`short_id`。若此前从未启用 Hy2，可无 `hysteria2_password`；若曾跑过 Phase 2 全开，文件中可能仍有 UDP 相关字段（属正常） |
| 1-C4 | `etc/config.json` | 合法 JSON；在 **`--no-hysteria2 --no-tuic`** 下 **`inbounds` 中仅含 `vless`** |
| 1-C5 | `logs/sing-box.log` | 有内容或可追加 |
| 1-C6 | `sing-box.pid`（数据根下） | 存在且为数字 PID |

### D. sing-box 校验与进程

| ID | 步骤 | 期望结果 |
|----|------|----------|
| 1-D1 | `<数据根>\bin\sing-box.exe check -c <数据根>\etc\config.json` | **退出码 0** |
| 1-D2 | PowerShell：`Get-NetTCPConnection -LocalPort 8443`（端口与 init 一致） | **Listen**，且 PID 与 pid 文件或任务管理器中 sing-box 一致 |
| 1-D3 | 读取 `config.json` 中 VLESS 的 `listen_port` | 与 **`--port`** 一致 |

### E. 否定 / 回归（Phase 1 相关）

| ID | 步骤 | 期望结果 |
|----|------|----------|
| 1-E1 | 在无 `--force` 且 sing-box 已运行时再次 `init` | **失败**（非零退出），提示需停止或 `--force` |
| 1-E2 | `--no-vless --no-hysteria2 --no-tuic` | **失败**，提示至少启用一种协议 |

### F. 自动化测试（dev）

| ID | 步骤 | 期望 |
|----|------|------|
| 1-F1 | `pytest tests/ -q` | 通过（含端口校验与 `test_build_inbounds`） |

**Phase 1 通过标准：** 1-B、1-C、1-D 全部满足；§0 可选。

---

## Phase 2 验收（目标：**多协议** VLESS + Hy2 + TUIC）

### A. 全开默认（三协议）

| ID | 步骤 | 期望结果 |
|----|------|----------|
| 2-A1 | `python -m tulipbridge init --port 8443 --hy2-port 8446 --tuic-port 8447 --tls-sni tulipbridge.local --force` | 成功退出码 **0**；摘要列出 **三种协议** 及 **TCP + 两条 UDP** 端口 |
| 2-A2 | `etc/config.json` | `inbounds` 中含 **`vless`**、**`hysteria2`**、**`tuic`** 三类 |
| 2-A3 | `etc/tls/cert.pem`、`etc/tls/key.pem` | 存在 |
| 2-A4 | `etc/keys.json` | 含 `hysteria2_password`、`tuic_password`、`tls_cert_path`、`tls_key_path` |
| 2-A5 | `sing-box check -c etc/config.json` | **退出码 0** |

### B. 端口语义（TCP / UDP 独立 + 冲突检测）

| ID | 步骤 | 期望结果 |
|----|------|----------|
| 2-B1 | `--port 443 --hy2-port 443 --tuic-port 8445`（全开） | **成功**（TCP 443 与 UDP 443 可同时存在） |
| 2-B2 | `--hy2-port 8444 --tuic-port 8444`（Hy2 与 TUIC 同 UDP 端口） | **失败**，提示 UDP 端口冲突 |

### C. 协议开关

| ID | 步骤 | 期望结果 |
|----|------|----------|
| 2-C1 | `--no-hysteria2 --no-tuic` | `config.json` **仅 vless**；不要求 `etc/tls`（仅 VLESS 时不生成 QUIC 证书） |
| 2-C2 | `--no-vless --hysteria2 --tuic` | `config.json` **无 vless** 入站，仍有 **Hy2 + TUIC**；`keys.json` 仍含 **uuid**（供 TUIC） |

### D. 路由与文档提示（验收观察项）

| ID | 步骤 | 期望结果 |
|----|------|----------|
| 2-D1 | 阅读 init 末尾输出 | 明确提示 **WAN UDP** 转发 Hy2/TUIC 端口（不仅是 TCP） |
| 2-D2 | 提示自签证书 | 提及客户端需跳过校验或 Phase 3 订阅后再简化 |

### E. 可选：真实网络层（家庭宽带）

| ID | 步骤 | 期望 |
|----|------|------|
| 2-E1 | 路由器分别映射 **TCP**（VLESS）与 **UDP**（Hy2/TUIC）到主机 | 客户端分别测三条线路（手填参数，Phase 3 前无订阅链接） |
| 2-E2 | Windows 防火墙 | 放行对应 TCP/UDP 入站 |

---

## 验收记录模板（可复制）

```
日期：
环境：Windows / Linux / macOS，Python 版本：
数据根：

Phase 1：□ §0  □ 1-A  □ 1-B  □ 1-C  □ 1-D  □ 1-E  □ 1-F
Phase 2：□ 2-A  □ 2-B  □ 2-C  □ 2-D  □ 2-E（可选）

阻塞项与备注：
```

---

## 说明

- **Phase 1 与 Phase 2** 在代码上共用同一 `init` 流程；隔离 Phase 1 专项验收请使用 **`--no-hysteria2 --no-tuic`**。
- **权威说明**以仓库内 [README.md](../README.md)、[ROADMAP.md](../ROADMAP.md) 与源码为准。
