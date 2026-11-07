# 9router-watchdog.ps1
# Continuous keep-alive watchdog for 9Router daemon & supervisor.
# Ensures 9Router (port 20127), local bridge (port 20128), and supervisor stay running 24/7.
$ErrorActionPreference = "SilentlyContinue"

# Single-Instance Guard
$myPid = $PID
$wdPattern = '-File\s+["'']?[^"'']*9router-watchdog\.ps1'
$existing = Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" | Where-Object { 
    $_.ProcessId -ne $myPid -and $_.CommandLine -match $wdPattern 
}
if ($existing) {
    Exit
}

$port = 20127
$supervisorScript = Join-Path $PSScriptRoot "9router-supervisor.ps1"
$startScript = Join-Path $PSScriptRoot "start-9router.ps1"
$hiddenRunner = Join-Path $PSScriptRoot "run-hidden.vbs"

function Start-HiddenScript([string]$scriptPath) {
    if (Test-Path $scriptPath) {
        $startup = [wmiclass]"Win32_ProcessStartup"
        $startupConfig = $startup.CreateInstance()
        $startupConfig.ShowWindow = 0
        $process = [wmiclass]"Win32_Process"
        $cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$scriptPath`""
        $process.Create($cmd, $null, $startupConfig) | Out-Null
    }
}

while ($true) {
    try {
        # 1. Guarantee supervisor is running
        $supPattern = '-File\s+["'']?[^"'']*9router-supervisor\.ps1'
        $sup = Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" | Where-Object { 
            $_.CommandLine -match $supPattern 
        }
        if (-not $sup) {
            Start-HiddenScript $supervisorScript
        }

        # 2. Guarantee port 20127 is listening
        $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        if (-not $conn) {
            Start-HiddenScript $startScript
        }
    } catch {
        # Keep watchdog loop alive
    }

    Start-Sleep -Seconds 15
}
