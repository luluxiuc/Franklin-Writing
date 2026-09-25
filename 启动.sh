#!/usr/bin/env bash
# 富兰克林写作工具 — macOS / Linux 启动脚本
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo "找不到 python3。请先安装 Python 3.10 或更高版本。"
  exit 1
fi
echo "正在启动富兰克林写作工具……浏览器会自动打开。按 Ctrl+C 结束。"
exec python3 app/fk_server.py
