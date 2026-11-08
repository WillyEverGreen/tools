@echo off
rem Re-register the 9Router task elevated, which upgrades it to boot-start (S4U).
powershell.exe -NoProfile -Command "Start-Process -FilePath 'C:\tools\9router\register-boot-task.cmd' -Verb RunAs"
exit /b %errorlevel%
