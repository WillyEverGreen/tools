@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$conns = Get-NetTCPConnection -LocalPort 20127 -ErrorAction SilentlyContinue; " ^
  "if (-not $conns) { Write-Host '[9Router] Not running.' -ForegroundColor Yellow; exit 0 } " ^
  "foreach ($p in ($conns | Select-Object -ExpandProperty OwningProcess -Unique)) { " ^
  "  Stop-Process -Id $p -Force -ErrorAction SilentlyContinue; " ^
  "  Write-Host ('[9Router] Stopped PID ' + $p) -ForegroundColor Green " ^
  "}"
