@echo off
chcp 65001 >nul
title NEOCORE STUDIO - Outreach Status Monitor
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0check_status.ps1"

echo.
echo Нажмите любую клавишу для закрытия...
pause >nul
