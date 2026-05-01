# 本地准备与中方异步交接（荷兰 / 服务端先做尽）

适用场景：你在**荷兰或本机**部署 TulipBridge，中国家属或同事需要用手机 **Shadowrocket** 连接，但双方**不便实时语音联调**。本文把「你这边能独立完成的事」和「必须中方配合的最后一步」分开写。

端到端命令步骤仍以 [HANDS_ON_WINDOWS_ZH.md](HANDS_ON_WINDOWS_ZH.md) 为准；客户端版本提示见 [SHADOWROCKET.md](SHADOWROCKET.md)。

---

## 一、你独自能做完的部分（不要求中方在线）

按重要性排列，建议逐项打勾。

### 1. 环境与产物

- [ ] 已在服务器或本机完成 **`tulipbridge init`**（或 **`--portable`**），`etc/config.json`、`etc/keys.json` 存在，`sing-box` 能通过 **`sing-box check`**（初始化流程里已包含）。
- [ ] **`tulipbridge status`** 显示 **sing-box running**（或你认可的在跑状态），且 **VLESS 对应 TCP 端口**在本机探测为 **`listen_ok`**（同一文档 Phase 5 行为）。
- [ ] **`tulipbridge update`** 能看到 **出口公网 IPv4**，并与路由器管理页里的 **WAN IP** 对照：若长期不一致，先处理 **CGNAT / 端口映射 / 双 NAT**，再让中方测。

### 2. 网络与防火墙

- [ ] **Windows 防火墙**（或 Linux 防火墙）已对你在 **`init` 里使用的端口**放行 **入站**（TCP VLESS + UDP Hy2/TUIC）。参见手把手文档 **第七步**。
- [ ] **路由器**已将 **WAN → 这台机器的 TCP/UDP 端口**映射一致（从外网访问时必填）。手把手文档 **「和手机不在同一 WiFi」** 一节。
- [ ] 记下未来将写入分享链接的 **`--public-host`**：**公网 IP** 或 **DDNS 域名**（与中方手机上看到的「服务器地址」必须一致）。

### 3. 订阅与二维码（无中方也可生成）

- [ ] 使用 **`--public-host`**（指向上述公网 IP 或域名）完成 **`init`**，或事后执行：  
  **`tulipbridge links --public-host 你的公网IP或域名`**  
  生成 **`subscribe/uris-plain.txt`**、**`subscription.txt`**、**`qr-*.png`**。
- [ ] 本地打开 **`uris-plain.txt`** 核对 **端口**、**host** 是否与路由器映射一致。

### 4. 可选：局域网烟雾测试

若家中有第二台设备连 **同一 WiFi**，可将 **`--public-host`** 临时设为 **电脑局域网 IP**，先在同 WiFi 下试连通。**不能代替**从中国蜂窝网络或跨省宽带到你家 WAN 的真实路径测试。

---

## 二、打包给中方「离线交接」的最小集合

不要求对方与你同时在线；通过微信 / 邮件 / 网盘发送即可。

建议至少包含：

| 内容 | 说明 |
|------|------|
| **`qr-vless-reality.png`**（或对应协议的 PNG） | 优先扫码导入 |
| **一行 `vless://…`** | 可从 **`uris-plain.txt`** 复制，便于「从剪贴板导入」 |
| **Shadowrocket 版本提示** | 摘抄自 [SHADOWROCKET.md](SHADOWROCKET.md) 的建议最低版本（以 App Store 为准） |
| **端口与协议顺序说明（可选）** | 建议先试 **VLESS（TCP）**，再试 **UDP** 线路 |

**不必**要求对方会命令行；步骤口头概括为：**安装 Shadowrocket → 扫码或粘贴链接 → 打开开关 → 先试 TCP 节点**。

---

## 三、唯一强烈依赖中方的一步（最后真实测试）

以下只能从**中国大陆典型网络环境**验证：

- GFW 路径、运营商对 **UDP / QUIC** 的策略、蜂窝与 Wi-Fi 差异等。

建议流程（可完全异步）：

1. 对方导入节点后，**先连 VLESS（TCP）**，确认能否访问网页。
2. 再根据需要试用 **Hysteria 2 / TUIC**。
3. 若失败，请对方异步反馈：**节点页报错文案、是否试过切换 4G/5G、截图（可选）**。你根据报错再改端口、SNI、`--public-host` 或防火墙，重新 **`links`** 后发新一版文件即可。

---

## 四、本地无法替代的局限（预期管理）

- **从中国大陆到你家宽带的端到端链路**只能通过中方实测确认。
- **UDP 不稳定**时以 **VLESS Reality（TCP）** 为主力（项目设计如此）。
- **动态公网 IP** 变化后：在中国方测试前，运行 **`tulipbridge update`** 自查出口 IP，并 **`tulipbridge links --public-host …`** 刷新订阅文件再发给对方。

---

## 五、相关命令速查

```text
tulipbridge status
tulipbridge update
tulipbridge links --public-host <公网IP或域名>
```

全局选项 **`--portable` / `--data-dir`** 与其它子命令的写法见 [README.md](../README.md)。
