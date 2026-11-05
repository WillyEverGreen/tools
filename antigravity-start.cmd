@echo off
if exist "%USERPROFILE%\tools\antigravity-auto-submit\auto-accept.js" (
  node "%USERPROFILE%\tools\antigravity-auto-submit\auto-accept.js" start %*
) else if exist "%~dp0daemon\auto-accept\auto-accept.js" (
  node "%~dp0daemon\auto-accept\auto-accept.js" start %*
) else (
  auto-accept start %*
)
