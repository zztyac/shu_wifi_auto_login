#!/bin/zsh

# shu校园网 Wi-Fi 一键登录脚本

# 若需要自定义账号密码，可提前在此脚本前导出环境变量：
#   export WIFI_USERNAME="你的账号"
#   export WIFI_PASSWORD="你的密码"

# 进入脚本所在目录，保证可以找到 Python 源文件。
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# 校验是否安装了 python3，并提示安装方式。
if ! command -v python3 >/dev/null 2>&1; then
  echo "未检测到 python3，请先通过 App Store 或官网安装 Python 3。"
  read -r "?按回车退出"
  exit 1
fi

# 执行登录脚本，捕获退出状态。
python3 "$SCRIPT_DIR/shu_wifi_login.py"
status=$?

# 友好提示，并阻塞窗口，方便查看输出。
if [ $status -eq 0 ]; then
  echo ""
  echo "✅ 已尝试登录shu校园网 Wi-Fi。"
else
  echo ""
  echo "⚠️ 登录过程出现错误，退出码：$status"
fi

read -r "?按回车关闭窗口"

