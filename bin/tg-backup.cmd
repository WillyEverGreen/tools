@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "SCRIPT=%SCRIPT_DIR%tg_backup.py"
if not exist "%SCRIPT%" set "SCRIPT=%~dp0..\src\tg_backup\tg_backup.py"

where uv >nul 2>nul
if %ERRORLEVEL% equ 0 (
  uv run "%SCRIPT%" %*
) else (
  where py >nul 2>nul
  if %ERRORLEVEL% equ 0 (
    py "%SCRIPT%" %*
  ) else (
    python "%SCRIPT%" %*
  )
)

