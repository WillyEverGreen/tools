@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\scripts\update-9router.ps1"
exit /b %errorlevel%
