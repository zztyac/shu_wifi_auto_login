# 上大校园网 Wi-Fi 自动登录工具

## 项目简介

本仓库提供用于上大校园网 Portal 的自动登录脚本，包含：
- `shu_wifi_login.py`：核心 Python 登录/注销逻辑，**支持自动尝试多个校区的登录 URL**。
- `run_shu_wifi_login.command`：macOS 双击即用的一键登录脚本。

### 功能特性

- ✅ **自动适配多校区**：脚本会自动尝试不同校区的登录页面 URL，找到可用的即使用，无需手动切换。
- ✅ **支持环境变量配置**：可通过环境变量设置账号密码，避免硬编码。
- ✅ **错误处理完善**：区分登录失败和网络错误，提供清晰的错误提示。

## 环境准备

- macOS（其他系统可直接使用 Python 脚本）。
- Python 3.8+。
- `requests` 库（可通过 `pip install requests` 安装）。

## 使用方式

### 1. 命令行执行

1. （可选）设置账号密码环境变量：
   ```shell
   export WIFI_USERNAME="你的校园网账号"
   export WIFI_PASSWORD="你的校园网密码"
   ```
   如未设置，将使用 `PortalCredentials` 中的默认值。
2. 在仓库目录下运行：
   ```shell
   python3 shu_wifi_login.py
   ```

### 2. macOS 双击脚本

1. 首次使用先赋予脚本执行权限：
   ```shell
   chmod +x /Users/x x x/Desktop/shu_wifi_login/run_shu_wifi_login.command
   ```
2. 直接双击 `run_shu_wifi_login.command`，按提示完成登录。

## 常见问题

- **未安装 Python 3**：请从 [Python 官网](https://www.python.org/downloads/) 下载并安装。
- **账号/密码错误**：确认环境变量或脚本中的凭证是否填写正确。
- **网络异常**：脚本会返回退出码 2 并提示 `Network error`，可稍后重试。
- **多校区支持**：脚本已内置多个校区的登录 URL，会自动尝试，无需手动配置。如果所有校区都失败，请检查网络连接或账号信息。


