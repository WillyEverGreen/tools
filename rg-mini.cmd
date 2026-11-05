@echo off
C:\tools\rg.exe -M 150 -n %* | node "C:\tools\line-cap.js" 20