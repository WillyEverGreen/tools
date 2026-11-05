@echo off
setlocal
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator privileges to stop MITM...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd.exe -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

node "d:\EXPERIMENTS PROJECTS\9router\scripts\antigravity-mitm.js" stop
echo.
pause
