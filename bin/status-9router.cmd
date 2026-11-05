@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$conn = Get-NetTCPConnection -LocalPort 20127 -ErrorAction SilentlyContinue; " ^
  "if ($conn) { Write-Host '[9Router] Running on port 20127 (PID: ' ($conn | Select-Object -First 1 -ExpandProperty OwningProcess) ')' -ForegroundColor Green } " ^
  "else { Write-Host '[9Router] Stopped (port 20127 not listening)' -ForegroundColor Red }"
