@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0clean-temp.ps1" %*

