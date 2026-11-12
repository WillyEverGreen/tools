# update-9router.ps1 - rebuild local cli/app (or install npm with -Npm) and restart the keep-alive stack.
#
# The stack lives behind the "9Router" scheduled task, so the update is:
#   stop the task -> rebuild cli/app (or npm replace) -> start the task again
# Killing the server while the supervisor is live would just make the supervisor
# restart the old code from a half-replaced directory.
param(
    [switch]$Npm
)

$ErrorActionPreference = "Continue"

$ctl = "C:\tools\9router\9r-ctl.ps1"
$cfgPath = "C:\tools\9router\config.json"
$buildScript = $null

if (-not $Npm -and (Test-Path $cfgPath)) {
    try {
        $cfg = Get-Content -Raw -Path $cfgPath | ConvertFrom-Json
        if ($cfg.appDir -and ($cfg.appDir -match '[\\/]cli[\\/]app$')) {
            $repoRoot = Split-Path (Split-Path $cfg.appDir -Parent) -Parent
            $candidate = Join-Path $repoRoot "cli\scripts\build-cli.js"
            if (Test-Path $candidate) {
                $buildScript = $candidate
            }
        }
    } catch {
        Write-Host "[9Router] Warning: could not parse $cfgPath ($($_.Exception.Message))" -ForegroundColor Yellow
    }
}

Write-Host "[9Router] Stopping the running stack..."
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $ctl stop

if ($buildScript) {
    Write-Host "[9Router] Rebuilding local cli/app bundle via $buildScript..."
    & node $buildScript
    $updateExit = $LASTEXITCODE
} else {
    Write-Host "[9Router] Installing latest 9router from npm..."
    & npm.cmd install -g 9router@latest
    $updateExit = $LASTEXITCODE
}

if ($updateExit -ne 0) {
    Write-Host "[9Router] Update failed (exit $updateExit) - restarting the existing version." -ForegroundColor Red
}

Write-Host "[9Router] Starting the stack..."
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $ctl start

exit $updateExit
