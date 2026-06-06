#!/bin/zsh

# 上大（SHU）校园网 Wi-Fi 一键登录脚本
#
# 账号密码请在同目录的 config.json 中配置（参考 config.example.json）：
#   {"username": "你的学号", "password": "你的密码"}
# 也可通过环境变量 WIFI_USERNAME / WIFI_PASSWORD 提供。

# 进入脚本所在目录，保证可以找到 Python 源文件与配置。
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# 校验是否安装了 python3，并提示安装方式。
if ! command -v python3 >/dev/null 2>&1; then
  echo "未检测到 python3，请先通过 App Store 或官网安装 Python 3。"
  read -r "?按回车退出"
  exit 1
fi

# 自动检测并安装 requests 依赖。
if ! python3 -c "import requests" >/dev/null 2>&1; then
  echo "正在安装依赖 requests ..."
  python3 -m pip install --user requests || \
    python3 -m pip install --user --break-system-packages requests
fi

# 执行登录脚本，捕获退出状态。
# 注意：zsh 中 status 是只读内置变量，这里改用 exit_code。
python3 "$SCRIPT_DIR/shu_wifi_login.py"
exit_code=$?

# 友好提示，并阻塞窗口，方便查看输出。
if [ $exit_code -eq 0 ]; then
  echo ""
  echo "✅ 已完成上大校园网 Wi-Fi 登录流程。"
else
  echo ""
  echo "⚠️ 登录过程出现错误，退出码：$exit_code"
fi

read -r "?按回车关闭窗口"
