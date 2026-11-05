@echo off
C:\tools\rg.exe -M 150 -n %* | node "%~dp0..\src\utils\line-cap.js" 20
