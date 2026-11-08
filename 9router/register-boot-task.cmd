@echo off
rem register-boot-task.cmd - runs task registration elevated (UAC) and records the result.
set "ROOT=%~dp0"
if not exist "%ROOT%logs" mkdir "%ROOT%logs"
del /q "%ROOT%logs\install-task.exit" >nul 2>&1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT%install-task.ps1" > "%ROOT%logs\install-task.log" 2>&1
echo %errorlevel%> "%ROOT%logs\install-task.exit"
exit /b %errorlevel%
