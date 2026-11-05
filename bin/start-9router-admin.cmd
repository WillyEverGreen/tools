@echo off
powershell.exe -NoProfile -Command "Start-Process powershell -ArgumentList '-NoProfile -ExecutionPolicy Bypass -Command \"cmd.exe /c stop-9router; cmd.exe /c start-9router\"' -Verb RunAs"
