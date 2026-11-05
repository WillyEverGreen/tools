@echo off
setlocal
cd /d "D:\FullStack Projects\diskmax"

echo [DiskMax Desktop] Starting local engine...
start /b py server.py > nul 2>&1
timeout /t 1 /nobreak > nul

echo [DiskMax Desktop] Launching Desktop Window...
start msedge.exe --app=http://localhost:1420 --window-size=1180,780 --app-id=diskmax-desktop
exit /b 0
