@echo off
rem Quick PC health check: disks, SSD, Defender, battery, power plan, uptime, RAM, startup apps. Changes nothing.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0pc-care.ps1" -Check -Quiet -Full
