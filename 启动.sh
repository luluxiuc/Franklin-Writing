#!/usr/bin/env bash
# 富兰克林写作工具 — macOS / Linux 启动脚本
# Franklin Writing — launcher for macOS / Linux
#
# 注意：echo 的每个参数都要有配对的引号。
# 这里出过一次事故：删多余引号时删掉了结尾那一个，脚本把下一行 exec 吞进了字符串。
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo "找不到 python3。请先安装 Python 3.10 或更高版本。"
  echo "Python 3.10+ not found. Please install it first."
  exit 1
fi
echo "正在启动富兰克林写作工具……浏览器会自动打开。按 Ctrl+C 结束。"
echo "Starting Franklin Writing... the browser opens by itself. Ctrl+C to stop."
exec python3 app/fk_server.py
