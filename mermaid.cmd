@echo off
if exist "%APPDATA%\npm\mmdc.cmd" (
  "%APPDATA%\npm\mmdc.cmd" %*
) else (
  npx -y @mermaid-js/mermaid-cli %*
)
