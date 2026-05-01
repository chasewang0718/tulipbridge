# 外网端口探测 — 新手分步说明（中文）

目的：确认 **互联网上的客户端** 能访问你家路由器 **WAN 公网 IP** 上映射到 TulipBridge 机器的端口。  
**只在自家网络里测**（同一 WiFi）通常不够，因为数据没走「从你运营商 WAN 进来」那条路径。

---

## 第一步：在本机确认要测哪些端口

在运行 TulipBridge 的电脑上执行：

```bash
tulipbridge status
```

记下输出里与 **`config.json`** 相关的端口，至少包括：

| 协议 | 传输 | 你要记住的端口 |
|------|------|----------------|
| VLESS-Reality | **TCP** | 例如 `443`（若你用默认） |
| Hysteria 2 | **UDP** | 例如 `8444` |
| TUIC | **UDP** | 例如 `8445` |

端口号以 **`status`** 为准（可能与默认值不同）。

---

## 第二步：确认你不是 CGNAT（否则外网映射常常无效）

在同一台机器上：

```bash
tulipbridge update
```

看输出的 **公网 IPv4**，再打开路由器管理页面对照 **WAN IP**：

- 若两者 **长期一致**，才有可能从外网打到你家端口。
- 若路由器 WAN 是 **`100.64.x.x`** 等私网段，或与 `update` 看到的公网 IP **始终对不上**，多半是 **CGNAT / 多层 NAT**，需要先解决网络架构（见 [FAQ.md](FAQ.md)），否则后面探测「通了」也不稳定。

---

## 第三步：确认路由器与系统防火墙已放行

未完成本节就做外网探测，结果**不可靠**（容易误判成「运营商问题」）。总体要做两件事：**路由器把 WAN 端口转到你的电脑**，**电脑防火墙放行同一端口**。通用概念仍见 [ROUTER_NAT.md](ROUTER_NAT.md)。

下文端口请一律以你 **`tulipbridge status`** 为准；下面用占位符 **`TCP_VLESS`**、**`UDP_HY2`**、**`UDP_TUIC`** 表示（例如你可能是 `8443` / `8446` / `8447`）。

### 3A. 先记下运行 TulipBridge 的那台电脑的局域网 IP（LAN）

**Windows（推荐先做）：**

1. 在本机打开 **PowerShell** 或 **cmd**，执行：`ipconfig`
2. 找到**当前正在上网**的那块网卡（有线以太网 / WLAN）。
3. 看该行 **`IPv4 Address . . . . . . . . . . . . :`**，例如 `192.168.1.42` —— 这就是路由器转发规则里要填的 **「内部主机 / 目标 IP」**。
4. 若有多块网卡或虚拟机网卡，不要选错；以能访问路由器管理页、且 TulipBridge 正在跑的连接为准。
5. （强烈建议）在路由器里给这台机器做 **DHCP 静态绑定**，或在本机设静态 IPv4，避免重启后 LAN IP 变了，转发全部失效。

记下：**`LAN_IP`** = `____________`

### 3B. 在路由器里添加端口转发（WAN → LAN_IP）

各品牌菜单名称不同，常见英文/中文关键词：**Port Forwarding**、**Virtual Server**、**NAT**、**端口映射**、**端口转发**、**IPv4 防火墙规则里的 DNAT**。DSL/光纤路由可能在 **「Internet」→「Security」→「Port forwarding」** 一类路径下。

对 **每一个** 协议 + 端口 **各建一条规则**（不要指望一条规则同时覆盖 TCP 和 UDP，除非界面明确支持且你已拆开填写）：

| 用途 | 协议 | 外部端口 | 内部 IP | 内部端口 |
|------|------|-----------|---------|-----------|
| VLESS-Reality | **TCP** | **`TCP_VLESS`** | **`LAN_IP`** | **`TCP_VLESS`** |
| Hysteria 2 | **UDP** | **`UDP_HY2`** | **`LAN_IP`** | **`UDP_HY2`** |
| TUIC | **UDP** | **`UDP_TUIC`** | **`LAN_IP`** | **`UDP_TUIC`** |

**填写时注意：**

- **外部端口**与**内部端口**一般填**相同数字**（与 `status` 一致）。
- **内部 IP** 必须是 **3A** 里那台电脑的 **`LAN_IP`**。
- **Hy2 / TUIC 两条都是 UDP**；若只转 TCP、不转 UDP，手机端 UDP 线路会失败。
- 保存后若路由器有 **「应用 / 保存」**，务必点生效；部分型号需要重启路由。

### 3C. Windows 防火墙：放行入站 TCP / UDP

仍假设端口为 **`TCP_VLESS`**、**`UDP_HY2`**、**`UDP_TUIC`**（请改成你的真实端口）。

**图形界面（适合新手）：**

1. **Win + R** → 输入 `wf.msc` → 回车，打开 **高级安全 Windows Defender 防火墙**。
2. 左侧点 **入站规则** → 右侧 **新建规则**。
3. 选 **端口** → **下一步**。
4. **TCP**，**特定本地端口**，填入 **`TCP_VLESS`**（如 `8443`）→ **下一步**。
5. **允许连接** → **下一步** → 配置文件（域/专用/公用按你网络勾选，不确定可全选）→ **下一步**。
6. 名称填例如 `TulipBridge VLESS TCP` → **完成**。
7. **再重复两次「新建规则」**，选 **UDP**，端口分别填 **`UDP_HY2`**、**`UDP_TUIC`**（如 `8446`、`8447`），名称可写 `TulipBridge Hy2 UDP`、`TulipBridge TUIC UDP`。

若你使用第三方安全软件，可能还要在它的防火墙里同样放行，或暂时排除冲突项。

**PowerShell（管理员）一键示例（端口请自行替换）：**

```powershell
New-NetFirewallRule -DisplayName "TulipBridge VLESS TCP" -Direction Inbound -Protocol TCP -LocalPort 8443 -Action Allow
New-NetFirewallRule -DisplayName "TulipBridge Hy2 UDP" -Direction Inbound -Protocol UDP -LocalPort 8446 -Action Allow
New-NetFirewallRule -DisplayName "TulipBridge TUIC UDP" -Direction Inbound -Protocol UDP -LocalPort 8447 -Action Allow
```

### 3D. Linux（服务器）简要：`ufw` 示例

若 TulipBridge 跑在 Linux 上（端口替换为你的 `status`）：

```bash
sudo ufw allow 8443/tcp comment 'TulipBridge VLESS'
sudo ufw allow 8446/udp comment 'TulipBridge Hy2'
sudo ufw allow 8447/udp comment 'TulipBridge TUIC'
sudo ufw reload
```

### 自检（仍在本机）

- 再执行 **`tulipbridge status`**：应仍为 **sing-box running**，且 **TCP … listen_ok**（与第一步一致）。
- 路由器、防火墙改完后，再进行文档 **第四步及以后** 的外网探测。

---

## 第四步：选一个「外网视角」的测试环境

你必须让探测流量从 **公网** 到达你家 WAN，任选其一：

| 方式 | 适合谁 |
|------|--------|
| **A. 一台境外/境内 VPS**（Linux，有 SSH） | 最可靠，推荐 |
| **B. 手机开蜂窝数据** + 在线端口检测网站 | TCP 可试；注意网站是否可信、是否测的是你当前预期 IP |
| **C. 请大陆亲友从他家网络试连** | 接近真实联调，但不是「可控探针」 |

**不要**只用家里第二台设备连同一 WiFi 当「外网测试」（那是内网或旁路，不等于 WAN 进来）。

下面以 **VPS（方式 A）** 为主写命令；没有 VPS 时，TCP 可临时用方式 B 做粗测。

---

## 第五步：确认当前公网 IP（探针要连谁）

在 TulipBridge 机器或路由器上确认 **`tulipbridge update`** 显示的公网 IP，记为 **`YOUR_WAN_IP`**。  
若你用 **DDNS 域名**，探针也可以对该域名做解析后再连（与订阅里的主机名一致即可）。

---

## 第六步：测 TCP（VLESS 端口）

在 **VPS** 上（把 **`YOUR_WAN_IP`** 和 **`TCP_PORT`** 换成你的值，例如 `443`）：

```bash
# 常见工具：nc (netcat)
nc -vz YOUR_WAN_IP TCP_PORT
```

- 显示 **succeeded** / **open** 一类结果 → 从该 VPS 看，**TCP 端口可达**。
- **Connection refused** → 往往是对端有防火墙拒绝或进程未监听。
- **Timeout** → 端口转发、运营商封锁、或 IP 不对；回到第二～三步排查。

仅有 Windows VPS 时，可用 PowerShell（在远端执行）：

```powershell
Test-NetConnection -ComputerName YOUR_WAN_IP -Port TCP_PORT
```

看 **`TcpTestSucceeded : True`**。

---

## 第七步：测 UDP（Hy2 / TUIC）——比 TCP 难

UDP **无连接**，很多在线「端口扫描」网站 **不测 UDP** 或不可靠。推荐：

1. **在 VPS 上用 `nc` 发 UDP 探测**（行为因系统/netcat 版本而异，可能只看到「是否收到 ICMP 不可达」）：  
   ```bash
   nc -u -vz YOUR_WAN_IP UDP_PORT
   ```  
   结果要结合 TulipBridge 端 **`sing-box` 是否在监听**、路由器 UDP 转发是否开启一起判断。

2. **更实际的验证**：在客户端用 **Hysteria 2 / TUIC** 节点试连（例如 Shadowrocket），能握手成功即说明 UDP 路径大致可用。

若 TCP（VLESS）通而 UDP 不通，常见于运营商对 UDP/QoS；项目设计里可用 **VLESS TCP 打底**，见 [ROADMAP.md](../ROADMAP.md) 附录。

---

## 第八步：记结果、再去做客户端联调

建议简单记录：

- 日期、测试地点（哪台 VPS / 哪种网络）
- **TCP_PORT** 结果：通 / 不通
- **UDP_PORT** 结果：通 / 不通 / 仅客户端实测

完成后，异步交接清单见 [PREP_AND_CHINA_HANDOFF_ZH.md](PREP_AND_CHINA_HANDOFF_ZH.md)。

---

## 常见新手误区

1. **在同一台路由器下的 WiFi 测「外网 IP:端口」** —— 很多路由器 **不支持 hairpin NAT**，结果容易误导；请用 VPS 或蜂窝数据。
2. **忘开 UDP 转发** —— Hy2/TUIC 必须单独建 **UDP** 规则，不是只转 TCP。
3. **公网 IP 变了但未更新 DDNS / 未重新 `links`** —— 客户端连的是旧地址；先 `tulipbridge update` 与 `tulipbridge links`（见 [QUICKSTART.md](QUICKSTART.md)）。

---

## 与本文档的关系

设计背景与局限： [PORT_PROBE.md](PORT_PROBE.md)。
