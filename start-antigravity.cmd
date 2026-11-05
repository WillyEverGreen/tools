@echo off
setlocal
:: Check for admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator privileges to activate MITM on port 443...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd.exe -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

node "d:\EXPERIMENTS PROJECTS\9router\scripts\antigravity-mitm.js" start
echo.
pause
