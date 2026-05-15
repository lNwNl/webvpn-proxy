# WebVPN代理服务器

用于渗透测试的WebVPN代理工具，自动将HTTP/HTTPS请求转换为WebVPN格式。

## 功能特性

- 透明代理：渗透测试工具只需配置HTTP代理即可
- 自动URL转换：将目标URL自动转换为WebVPN格式
- 会话管理：自动处理WebVPN登录和cookie维护
- HTTPS支持：通过mitmproxy支持HTTPS流量拦截

## 安装

使用uv管理依赖：

```bash
cd webvpn-proxy
uv sync
```

## 配置

编辑`config.json`：

```json
{
  "webvpn_url": "https://v.hbu.cn",
  "username": "你的用户名",
  "password": "你的密码",
  "cookie": null,
  "proxy_port": 8080,
  "log_level": "INFO",
  "ssl_insecure": true
}
```

或者使用cookie认证：

```json
{
  "webvpn_url": "https://v.hbu.cn",
  "username": null,
  "password": null,
  "cookie": "wengine_vpn_ticketv_hbu_cn=xxx; show_vpn=1; ...",
  "proxy_port": 8080,
  "log_level": "INFO",
  "ssl_insecure": true
}
```

## 使用方法

### 1. 启动代理

```bash
# 使用默认配置
uv run webvpn-proxy

# 指定配置文件
uv run webvpn-proxy -c my_config.json

# 指定端口
uv run webvpn-proxy -p 9090

# 调试模式
uv run webvpn-proxy -l DEBUG
```

### 2. 配置渗透测试工具

#### sqlmap
```bash
sqlmap -u "http://target/page?id=1" --proxy="http://127.0.0.1:8080"
```

#### nmap
```bash
nmap -sT --proxies http://127.0.0.1:8080 target_ip
```

#### curl
```bash
curl --proxy http://127.0.0.1:8080 http://target/path
```

#### 浏览器
设置HTTP代理为`127.0.0.1:8080`

### 3. HTTPS支持

对于HTTPS流量，需要安装mitmproxy的CA证书：

1. 启动代理后，访问`http://mitm.it`
2. 下载并安装对应平台的CA证书
3. 或者使用`--ssl-insecure`选项跳过证书验证

## 工作原理

```
渗透测试工具 → 本地代理(8080) → WebVPN服务器 → 目标服务器
```

1. 工具发送请求到本地代理
2. 代理拦截请求，提取目标URL
3. 将URL转换为WebVPN格式
4. 通过WebVPN会话发送请求
5. 将响应返回给工具

## 日志

日志文件：`webvpn_proxy.log`

日志级别：
- `ERROR`: 只显示错误
- `INFO`: 显示基本信息（默认）
- `DEBUG`: 显示详细调试信息

## 故障排除

### 代理无法启动
1. 检查端口是否被占用
2. 检查配置文件格式是否正确
3. 检查WebVPN凭证是否有效

### 请求失败
1. 检查网络连接
2. 检查WebVPN会话是否过期
3. 查看日志文件获取详细信息

### HTTPS证书错误
1. 安装mitmproxy CA证书
2. 或使用`--ssl-insecure`选项

## 开发

### 项目结构
```
webvpn-proxy/
├── webvpn_core.py      # WebVPN核心类
├── proxy_core.py       # 代理核心逻辑
├── webvpn_proxy.py     # mitmproxy addon
├── run.py             # 启动脚本
├── config.json        # 配置文件
└── pyproject.toml     # 项目配置
```

### 扩展开发
1. 修改`proxy_core.py`添加自定义逻辑
2. 在`webvpn_proxy.py`中添加mitmproxy钩子
3. 更新配置文件支持新的选项

## 许可证

仅供学习和授权测试使用。