@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match '9router-supervisor|9router-watchdog' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host ('[9Router] Stopped daemon PID ' + $_.ProcessId) -ForegroundColor Green }; " ^
  "$conns = Get-NetTCPConnection -LocalPort 20127, 20128 -ErrorAction SilentlyContinue; " ^
  "if ($conns) { foreach ($p in ($conns | Select-Object -ExpandProperty OwningProcess -Unique)) { if ($p -gt 0) { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue; Write-Host ('[9Router] Stopped server PID ' + $p) -ForegroundColor Green } } } else { Write-Host '[9Router] Server stopped.' -ForegroundColor Yellow }"

