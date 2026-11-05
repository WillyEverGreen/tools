@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "SCRIPT=%~dp0..\src\code_check.py"
if not exist "%SCRIPT%" set "SCRIPT=%~dp0..\src\code_check.py"

py "%SCRIPT%" %*

