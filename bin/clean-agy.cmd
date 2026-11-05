@echo off
setlocal
set "SCRIPT=%USERPROFILE%\tools\antigravity-auto-submit\scripts\antigravity_cleaner.py"
if not exist "%SCRIPT%" set "SCRIPT=%~dp0..\src\antigravity\antigravity_cleaner.py"
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
  py "%SCRIPT%" --ag %*
) else (
  python "%SCRIPT%" --ag %*
)

