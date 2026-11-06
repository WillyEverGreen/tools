# 9router-watchdog.ps1
# Continuous keep-alive watchdog for 9Router daemon & supervisor.
# Ensures 9Router (port 20127), local bridge (port 20128), and supervisor stay running 24/7.

$ErrorActionPreference = 'SilentlyContinue'
$port = 20127
$supervisorScript = Join-Path $PSScriptRoot "9router-supervisor.ps1"
$startScript = Join-Path $PSScriptRoot "start-9router.ps1"

function Ensure-SupervisorRunning {
    $sup = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "9router-supervisor\.ps1" }
    if (-not $sup) {
        $cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$supervisorScript`""
        Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = $cmd} | Out-Null
    }
}

while ($true) {
    # 1. Guarantee supervisor is running
    Ensure-SupervisorRunning

    # 2. Guarantee port 20127 is listening
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if (-not $conn) {
        if (Test-Path $startScript) {
            $cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$startScript`""
            Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = $cmd} | Out-Null
        }
    }

    Start-Sleep -Seconds 15
}
