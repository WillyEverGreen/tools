@echo off
setlocal enabledelayedexpansion

set "ACTION=%~1"

if /i "%ACTION%"=="help" goto help
if /i "%ACTION%"=="--help" goto help
if /i "%ACTION%"=="-h" goto help

if /i "%ACTION%"=="stop" (
    call "%~dp0stop-9router.cmd"
    exit /b %errorlevel%
)

if /i "%ACTION%"=="status" (
    call "%~dp0status-9router.cmd"
    exit /b %errorlevel%
)

if /i "%ACTION%"=="open" (
    start http://localhost:20127/dashboard
    exit /b 0
)

if /i "%ACTION%"=="quota" (
    start http://localhost:20127/dashboard/quota
    exit /b 0
)

if /i "%ACTION%"=="usage" (
    start http://localhost:20127/dashboard/usage
    exit /b 0
)

if /i "%ACTION%"=="accounts" (
    node --no-warnings "D:\EXPERIMENTS PROJECTS\9router\scripts\accounts-status.mjs" %2 %3
    exit /b %errorlevel%
)

if /i "%ACTION%"=="test" (
    node --no-warnings "D:\EXPERIMENTS PROJECTS\9router\scripts\accounts-test.mjs" %2
    exit /b %errorlevel%
)

if /i "%ACTION%"=="health" (
    node --no-warnings "D:\EXPERIMENTS PROJECTS\9router\scripts\accounts-status.mjs" --live %2 %3
    exit /b %errorlevel%
)

if /i "%ACTION%"=="update" (
    call "%~dp0update-9router.cmd"
    exit /b %errorlevel%
)

if /i "%ACTION%"=="models" (
    node "d:\EXPERIMENTS PROJECTS\9router\scripts\list-models.js"
    exit /b %errorlevel%
)

if /i "%ACTION%"=="restart" (
    call "%~dp0stop-9router.cmd"
    timeout /t 1 /nobreak >nul
    call "%~dp0start-9router.cmd"
    exit /b %errorlevel%
)

if /i "%ACTION%"=="dev" (
    cd /d "d:\EXPERIMENTS PROJECTS\9router"
    call "d:\EXPERIMENTS PROJECTS\9router\start.cmd"
    exit /b %errorlevel%
)

if /i "%ACTION%"=="" (
    call "%~dp0start-9router.cmd"
    exit /b %errorlevel%
)

if /i "%ACTION%"=="start" (
    call "%~dp0start-9router.cmd"
    exit /b %errorlevel%
)

:help
echo ===============================================================================
echo                      9ROUTER CLI (9r) - COMMAND REFERENCE
echo ===============================================================================
echo.
echo   Core Server Commands:
echo     9r               Start 9Router in background (port 20127)
echo     9r status        Check if 9Router is running and view PID
echo     9r stop          Stop the running 9Router server
echo     9r restart       Restart 9Router service cleanly
echo     9r update        Install latest 9router from npm and restart
echo     9r dev           Run 9Router in foreground with live terminal logs
echo.
echo   Web Dashboard Shortcuts:
echo     9r open          Open main Dashboard in default browser
echo     9r quota         Open Live Account Quota ^& Reset Timers page
echo     9r usage         Open Token ^& Usage Statistics page
echo.
echo   Model ^& Account Inspection:
echo     9r accounts      Health of every provider account ^(add a provider name to filter^)
echo     9r test          Run the gateway's connection test on every account ^(or one provider^)
echo     9r health        Same, plus a live test request per provider
echo     9r models        Print complete model catalog and CLI aliases
echo     9r help          Display this command reference
echo.
echo ===============================================================================
exit /b 0

