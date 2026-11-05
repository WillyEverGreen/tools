@echo off
if exist "%USERPROFILE%\tools\antigravity-auto-submit\kiro-auto-accept\kiro-auto-accept.js" (
  node "%USERPROFILE%\tools\antigravity-auto-submit\kiro-auto-accept\kiro-auto-accept.js" %*
) else if exist "%~dp0kiro-auto-accept\kiro-auto-accept.js" (
  node "%~dp0kiro-auto-accept\kiro-auto-accept.js" %*
) else (
  node "%~dp0kiro-auto-accept.js" %*
)
