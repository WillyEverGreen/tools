@echo off
C:\tools\ast-grep.exe run -p "%~1" %2 %3 %4 %5 %6 %7 %8 %9 | node "%~dp0..\src\utils\line-cap.js" 20

