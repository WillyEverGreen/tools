@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$conn = Get-NetTCPConnection -LocalPort 20127 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1; " ^
  "if ($conn) { Write-Host ('[9Router] Running on port 20127 (PID: ' + $conn.OwningProcess + ')') -ForegroundColor Green } " ^
  "else { Write-Host '[9Router] Stopped (port 20127 not listening)' -ForegroundColor Red }"

