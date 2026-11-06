# 9router-watchdog.ps1
# Continuous keep-alive watchdog for 9Router daemon.
# Ensures 9Router (port 20127) and local bridge stay running 24/7.

$ErrorActionPreference = 'SilentlyContinue'
$port = 20127
$startScript = Join-Path $PSScriptRoot "start-9router.ps1"

while ($true) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if (-not $conn) {
        if (Test-Path $startScript) {
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File $startScript
        }
    }
    Start-Sleep -Seconds 30
}

