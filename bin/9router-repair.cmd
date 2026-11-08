@echo off
rem 9router-repair - one-click (UAC) cleanup of orphaned 9Router processes.
powershell.exe -NoProfile -Command "Start-Process -FilePath 'C:\tools\9router\repair.cmd' -Verb RunAs"
exit /b %errorlevel%
