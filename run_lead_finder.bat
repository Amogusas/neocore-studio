@echo off
chcp 65001 >nul
title NEOCORE STUDIO // Multi-Niche Lead Discovery
cd /d "%~dp0"

echo =====================================================================
echo NEOCORE STUDIO // Multi-Niche Lead Discovery
echo =====================================================================
echo.
python lead_finder.py --all --count 3
echo.
echo Нажмите любую клавишу для завершения...
pause >nul
