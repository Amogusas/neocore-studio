@echo off
chcp 65001 >nul
title NEOCORE STUDIO - Automated 24/7 B2B Outreach Engine
cd /d "%~dp0"

echo =====================================================================
echo NEOCORE STUDIO // Autonomous 24/7 Cold Outreach Engine
echo =====================================================================
echo.
echo Режим: Непрерывный автономный цикл (24/7)
echo Дневной лимит: 30 писем/сутки
echo Рабочие часы: 09:00 - 19:00 (ночью безопасный режим ожидания)
echo Автопополнение: Включено (сбор свежих лидов по всем 19 нишам)
echo.
echo Для ручной остановки нажмите Ctrl+C.
echo.

:LOOP
python cold_outreach.py --loop --daily-limit 30 --delay 15
echo.
echo [WATCHDOG] Процесс завершился или был прерван. Перезапуск через 30 секунд...
timeout /t 30 /nobreak >nul
goto LOOP
