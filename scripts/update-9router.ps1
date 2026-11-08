# update-9router.ps1 — install the latest 9router and restart the keep-alive stack.
#
# The stack lives behind the "9Router" scheduled task, so the update is:
#   stop the task -> npm replace the files -> start the task again
# Killing the server while the supervisor is live would just make the supervisor
# restart the old code from a half-replaced directory.
$ErrorActionPreference = "Continue"

$ctl = "C:\tools\9router\9r-ctl.ps1"

Write-Host "[9Router] Stopping the running stack..."
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $ctl stop

Write-Host "[9Router] Installing latest 9router..."
& npm.cmd install -g 9router@latest
$npmExit = $LASTEXITCODE

if ($npmExit -ne 0) {
    Write-Host "[9Router] npm failed (exit $npmExit) - restarting the existing version." -ForegroundColor Red
}

Write-Host "[9Router] Starting the stack..."
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $ctl start

exit $npmExit
