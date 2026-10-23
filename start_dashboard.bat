@echo off
setlocal
cd /d "%~dp0"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_dashboard.ps1"
if errorlevel 1 (
  echo.
  echo Dashboard startup failed. Review the message above.
  pause
  exit /b 1
)

endlocal
