@echo off
rem tools: find and verify the CLIs in C:\tools.  tools list | find <word> | show <name> | doctor | categories   (add -Json for JSON)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools.ps1" %*
