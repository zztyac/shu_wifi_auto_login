# 上大校园网 Wi-Fi 自动登录工具

## 项目简介

本仓库提供用于上大校园网 Portal 的自动登录脚本，包含：
- `shu_wifi_login.py`：核心 Python 登录/注销逻辑，**自动抓取门户实时下发的登录参数**。
- `run_shu_wifi_login.command`：macOS 双击即用的一键登录脚本（会自动安装依赖）。

### 功能特性

- ✅ **自动抓取登录参数**：登录前主动访问外网探测地址，让门户把请求重定向到登录页，
  再从重定向 URL 中提取当时有效的 `queryString`（`wlanuserip` / `mac` / `url` 等）。
  这些参数是门户动态下发的会话令牌、会过期，因此**不再硬编码**，从根本上解决"过段时间就失效"的问题。
- ✅ **已在线自动识别**：若当前已经联网，脚本会直接提示"已在线"并退出，不重复登录。
- ✅ **凭证外部化**：账号密码放在本地 `config.json`（已被 `.gitignore` 忽略，不进入 git），
  也支持用环境变量提供，避免明文进代码。
- ✅ **依赖自动安装**：双击脚本会自动检测并安装 `requests`。
- ✅ **错误处理完善**：区分"已在线 / 登录失败 / 网络错误"，分别返回退出码 0 / 1 / 2。

## 环境准备

- macOS（其他系统可直接使用 Python 脚本）。
- Python 3.8+。
- `requests` 库（双击脚本会自动安装；手动安装：`pip3 install requests`）。

## 配置账号密码

复制示例配置并填入自己的凭证：

```shell
cp config.example.json config.json
```

然后编辑 `config.json`：

```json
{
  "username": "你的学号",
  "password": "你的密码",
  "service": "shu"
}
```

> `config.json` 已加入 `.gitignore`，不会被提交。也可改用环境变量：
> `export WIFI_USERNAME=...` 与 `export WIFI_PASSWORD=...`（优先级高于配置文件）。

## 使用方式

### 1. macOS 双击脚本（推荐）

1. 首次使用先赋予执行权限：
   ```shell
   chmod +x run_shu_wifi_login.command
   ```
2. 直接双击 `run_shu_wifi_login.command`，按提示完成登录。

### 2. 命令行执行

```shell
python3 shu_wifi_login.py          # 登录（默认）
python3 shu_wifi_login.py logout   # 注销
```

## 退出码

| 退出码 | 含义 |
| ------ | ---- |
| 0 | 登录成功，或当前已在线 |
| 1 | 登录失败（账号密码错误、门户拒绝等，详见提示） |
| 2 | 网络错误（连不上门户等） |

## 常见问题

- **提示"未找到账号密码"**：请确认 `config.json` 已创建并填好，或已设置环境变量。
- **提示"当前网络已在线"**：说明已经联网，无需再登录。
- **登录失败**：确认账号密码正确；若门户提示"WEB认证设备未注册"等，通常是参数问题，
  本脚本已通过自动抓取实时参数规避；如仍失败请重连 Wi-Fi 后再试。
- **未安装 Python 3**：请从 [Python 官网](https://www.python.org/downloads/) 下载安装。
