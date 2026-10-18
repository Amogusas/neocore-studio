[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "NEOCORE STUDIO // Монитор статуса фонового аутрича" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Проверка активных процессов
$procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -like "*python*" -and $_.CommandLine -like "*cold_outreach.py*" }
if ($procs) {
    Write-Host "[СТАТУС ПРОЦЕССА]: РАБОТАЕТ В ФОНЕ (ONLINE)" -ForegroundColor Green
    foreach ($p in $procs) {
        $memMB = [math]::Round($p.WorkingSetSize / 1MB, 1)
        Write-Host "  - PID: $($p.ProcessId) | Память: $memMB МБ"
    }
} else {
    Write-Host "[СТАТУС ПРОЦЕССА]: НЕ ЗАПУЩЕН (OFFLINE)" -ForegroundColor Yellow
    Write-Host "  (Для запуска используйте start_hidden_outreach.vbs или run_outreach_24_7.bat)"
}

Write-Host ""
Write-Host "---------------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "[СТАТИСТИКА БАЗЫ LEADS.CSV]:" -ForegroundColor White

$csvPath = Join-Path $PSScriptRoot "leads.csv"
if (Test-Path $csvPath) {
    $csv = Import-Csv $csvPath -Encoding UTF8
    $today = (Get-Date).ToString("yyyy-MM-dd")
    $total = $csv.Count
    $sent = ($csv | Where-Object { $_.status -eq "sent" }).Count
    $sent_today = ($csv | Where-Object { $_.status -eq "sent" -and $_.sent_at -like "$today*" }).Count
    $pending = ($csv | Where-Object { $_.status -eq "pending" }).Count

    Write-Host "  - Всего записей в базе: $total"
    Write-Host "  - Отправлено сегодня ($today): $sent_today / 30"
    Write-Host "  - Всего отправлено: $sent"
    Write-Host "  - Ожидают в очереди (pending): $pending"
} else {
    Write-Host "  Файл leads.csv пока не найден."
}

Write-Host ""
Write-Host "---------------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "[ПОСЛЕДНИЕ СОБЫТИЯ ИЗ OUTREACH.LOG]:" -ForegroundColor White

$logPath = Join-Path $PSScriptRoot "outreach.log"
if (Test-Path $logPath) {
    Get-Content $logPath -Tail 15 -Encoding UTF8 | ForEach-Object {
        Write-Host "  $_"
    }
} else {
    Write-Host "  Лог-файл outreach.log пока пуст."
}

Write-Host "=====================================================================" -ForegroundColor Cyan
