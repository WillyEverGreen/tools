@echo off
setlocal
set "SCRIPT=%USERPROFILE%\tools\antigravity-auto-submit\scripts\antigravity_cleaner.py"
if not exist "%SCRIPT%" set "SCRIPT=%~dp0antigravity_cleaner.py"
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
  py "%SCRIPT%" --check --ag %*
) else (
  python "%SCRIPT%" --check --ag %*
)
