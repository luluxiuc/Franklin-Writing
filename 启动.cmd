@echo off
rem ---------------------------------------------------------------
rem  Franklin Writing -- Windows launcher
rem
rem  IMPORTANT: keep this file pure ASCII, with CRLF line endings.
rem  cmd.exe parses a .cmd file line by line in the system OEM code
rem  page (GBK on a Chinese Windows), NOT in the code page set by
rem  `chcp`. A UTF-8 Chinese string therefore gets split mid-character
rem  and the leftover bytes get run as commands: the window flashes and
rem  closes, and the server never starts. Even a Chinese filename in a
rem  `rem` comment triggers it.
rem
rem  That bug is why the messages below are in English. A message you
rem  cannot read is bad; a launcher that silently does nothing is worse.
rem  The bash launcher is unaffected -- terminals are UTF-8, so its
rem  Chinese messages are fine.
rem ---------------------------------------------------------------

title Franklin Writing
cd /d "%~dp0"

set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY (
  where py >nul 2>nul && set "PY=py"
)

if not defined PY (
  echo.
  echo   Python not found.
  echo   Install Python 3.10 or newer, and tick
  echo   "Add python.exe to PATH" during setup.
  echo.
  echo   See README.md for the install guide.
  echo.
  pause
  exit /b 1
)

echo.
echo   Starting Franklin Writing...
echo   The browser opens by itself. Close this window to stop it.
echo.

%PY% "app\fk_server.py"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo.
  echo   Failed to start ^(exit code %RC%^).
  echo   Send the text above to the author.
  echo.
  pause
)
