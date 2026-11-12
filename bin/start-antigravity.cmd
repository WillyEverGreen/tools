@echo off
setlocal
set "NO_PAUSE="
if /i "%~1"=="--no-pause" set "NO_PAUSE=1"

:: Check for admin rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator privileges to activate MITM on port 443...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd.exe -ArgumentList '/c \"\"%~f0\" %*\"' -Verb RunAs"
    exit /b %errorlevel%
)

node "d:\EXPERIMENTS PROJECTS\9router\scripts\antigravity-mitm.js" start
set "EXIT_CODE=%errorlevel%"
echo.
if not defined NO_PAUSE pause
exit /b %EXIT_CODE%
