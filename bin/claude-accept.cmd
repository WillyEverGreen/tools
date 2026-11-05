@echo off
if exist "%USERPROFILE%\tools\antigravity-auto-submit\claude-auto-accept\claude-auto-accept.js" (
  node "%USERPROFILE%\tools\antigravity-auto-submit\claude-auto-accept\claude-auto-accept.js" %*
) else if exist "%~dp0claude-auto-accept\claude-auto-accept.js" (
  node "%~dp0claude-auto-accept\claude-auto-accept.js" %*
) else (
  node "%~dp0claude-auto-accept.js" %*
)
