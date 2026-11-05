@echo off
if exist "%LOCALAPPDATA%\OpenAI\Codex\bin" (
  for /f "delims=" %%I in ('dir /b /s "%LOCALAPPDATA%\OpenAI\Codex\bin\codex.exe" 2^>nul') do (
    "%%I" %*
    exit /b %ERRORLEVEL%
  )
)
echo Codex CLI binary not found in %%LOCALAPPDATA%%\OpenAI\Codex\bin.
