$ErrorActionPreference = 'Stop'
$port = 20127

# Stop the gateway listener and its cli.js wrapper so npm can replace the files.
Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
    Where-Object { $_.CommandLine -like '*node_modules\9router\*' } |
    ForEach-Object { Write-Host "[9Router] Stopping PID $($_.ProcessId)"; Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2

Write-Host '[9Router] Installing latest 9router...'
& npm.cmd install -g 9router@latest
$npmExit = $LASTEXITCODE

if ($npmExit -ne 0) { Write-Host "[9Router] npm failed (exit $npmExit); restarting the existing version." -ForegroundColor Red }
& "$PSScriptRoot\start-9router.ps1"
exit $npmExit
