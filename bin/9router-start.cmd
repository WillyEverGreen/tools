@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\tools\9router\9r-ctl.ps1" start
exit /b %errorlevel%
