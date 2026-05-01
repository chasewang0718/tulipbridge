# 路由器端口映射（WAN → TulipBridge 主机）

TulipBridge 监听 **TCP**（VLESS-Reality）和 **UDP**（Hysteria 2 / TUIC）。家里的路由器必须把 **公网 WAN IPv4** 上的 **相同端口号** 转发到运行 sing-box 的那台机器的 **局域网 IP**。

## 1. 确认监听端口

在服务器上执行：

```bash
tulipbridge status
```

记下 `config.json` 中的 **VLESS-Reality（TCP）**、**Hysteria 2（UDP）**、**TUIC（UDP）** 端口。

## 2. 查出服务器的局域网地址

在运行 TulipBridge 的电脑上查看 **局域网 IPv4**（例如 `192.168.1.50`）。建议使用 **DHCP 静态绑定（保留地址）** 或本机静态 IP，以免重启后转发规则失效。

## 3. 建立转发规则

在路由器管理后台（各厂商界面不同）：

1. 打开 **端口转发** / **虚拟服务器** / **NAT** 等同类菜单。
2. **每种协议、每个端口各建一条规则**：
   - **WAN TCP** `P` → **局域网 IP** 的 TCP `P`（VLESS）。
   - **WAN UDP** `P` → **局域网 IP** 的 UDP `P`（Hy2、TUIC 各端口分别添加）。

部分路由器把 **TCP** 与 **UDP** 分开列表；基于 QUIC 的协议 **必须** 配置 **UDP** 规则。

## 4. 电脑上的防火墙

在操作系统防火墙中允许上述 **TCP/UDP 入站**（Windows Defender 防火墙、`ufw` 等），针对 sing-box 进程或直接放行对应端口。

## 5. 验证

- **`tulipbridge update`**：显示的公网 IPv4 应与路由器 **WAN** 地址一致（排除 CGNAT — 见 [FAQ.md](FAQ.md)）。
- 从 **局域网以外**（例如手机蜂窝数据）测试连通性；仅在局域网内测试 **不能** 证明 WAN 转发有效。

## 示意图（概念）

```text
Internet ----[ WAN :443 TCP ]----> Router ----[ DNAT ]----> 192.168.x.x:443 (TulipBridge)
```

UDP 端口同理，把图中的 TCP 换成 UDP 即可。

## 延伸阅读

- Windows 手把手（中文）：[HANDS_ON_WINDOWS_ZH.md](HANDS_ON_WINDOWS_ZH.md)
- 外网可达性说明与局限：[PORT_PROBE.md](PORT_PROBE.md)
