@echo off
rem repair.cmd - elevated: kill orphaned 9Router processes and restart the task.
set "ROOT=%~dp0"
if not exist "%ROOT%logs" mkdir "%ROOT%logs"
del /q "%ROOT%logs\repair.exit" >nul 2>&1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT%repair.ps1" > "%ROOT%logs\repair.log" 2>&1
echo %errorlevel%> "%ROOT%logs\repair.exit"
exit /b %errorlevel%
