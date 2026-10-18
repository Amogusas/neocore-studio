@echo off
chcp 65001 >nul
title NEOCORE STUDIO // Stop Outreach
cd /d "%~dp0"

echo =====================================================================
echo NEOCORE STUDIO // Stopping Cold Outreach Background Processes
echo =====================================================================
echo.
echo Поиск и остановка процессов cold_outreach.py...
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*cold_outreach.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('[STOPPED] Процесс ID ' + $_.ProcessId + ' остановлен.') }"
echo.
echo Завершено.
timeout /t 3 >nul
