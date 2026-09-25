@echo off
chcp 65001 >nul
title 富兰克林写作工具
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo   找不到 python。请先安装 Python 3.10 或更高版本，
  echo   安装时记得勾选 "Add python.exe to PATH"。
  echo.
  pause
  exit /b 1
)

echo.
echo   正在启动富兰克林写作工具……
echo   浏览器会自动打开。用完直接关掉这个黑窗口就行。
echo.
python "app\fk_server.py"
if errorlevel 1 (
  echo.
  echo   启动失败。把上面的信息截图发给作者。
  pause
)
