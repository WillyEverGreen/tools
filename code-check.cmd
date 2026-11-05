@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "SCRIPT=%SCRIPT_DIR%code_check.py"
if not exist "%SCRIPT%" set "SCRIPT=C:\tools\code_check.py"

py "%SCRIPT%" %*
