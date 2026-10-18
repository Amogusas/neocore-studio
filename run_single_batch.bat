@echo off
chcp 65001 >nul
title NEOCORE STUDIO // Single Batch Outreach
cd /d "%~dp0"

echo =====================================================================
echo NEOCORE STUDIO // Single Batch Cold Outreach
echo =====================================================================
echo.
python cold_outreach.py
echo.
echo Нажмите любую клавишу для завершения...
pause >nul
