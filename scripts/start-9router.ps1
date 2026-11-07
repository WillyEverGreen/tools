# Starts the installed 9router server directly in the background with continuous supervisor & watchdog.
# Same environment the launcher builds: PORT/HOSTNAME + NODE_PATH with the bundled and runtime node_modules.

$port = 20127
$pkg  = Join-Path $env:APPDATA 'npm\node_modules\9router'
$app  = Join-Path $pkg 'app'
$node = if (Test-Path 'C:\Program Files\nodejs\node.exe') { 'C:\Program Files\nodejs\node.exe' } else { (Get-Command node.exe -ErrorAction SilentlyContinue).Source }
$server = if (Test-Path (Join-Path $app 'custom-server.js')) { Join-Path $app 'custom-server.js' } else { Join-Path $app 'server.js' }
$supervisorScript = Join-Path $PSScriptRoot "9router-supervisor.ps1"
$watchdogScript = Join-Path $PSScriptRoot "9router-watchdog.ps1"
$hiddenRunner = Join-Path $PSScriptRoot "run-hidden.vbs"

if (-not (Test-Path $server)) {
    Write-Host "[9Router] Not installed: $server (run: npm i -g 9router)" -ForegroundColor Red
    exit 1
}

function Start-HiddenProcess([string]$targetScript) {
    if (Test-Path $targetScript) {
        $startup = [wmiclass]"Win32_ProcessStartup"
        $startupConfig = $startup.CreateInstance()
        $startupConfig.ShowWindow = 0
        $process = [wmiclass]"Win32_Process"
        $cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$targetScript`""
        $process.Create($cmd, $null, $startupConfig) | Out-Null
    }
}

# 1. Check if supervisor is running; if not, launch detached via hidden runner
$supPattern = '-File\s+["'']?[^"'']*9router-supervisor\.ps1'
$sup = Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" | Where-Object { $_.CommandLine -match $supPattern }
if (-not $sup) {
    Start-HiddenProcess $supervisorScript
}

# 2. Check if watchdog is running; if not, launch detached via hidden runner
$wdPattern = '-File\s+["'']?[^"'']*9router-watchdog\.ps1'
$wd = Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" | Where-Object { $_.CommandLine -match $wdPattern }
if (-not $wd) {
    Start-HiddenProcess $watchdogScript
}

# 3. Wait for port 20127 to become ready
for ($i = 0; $i -lt 30; $i++) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        Write-Host "[9Router] Ready and supervised on http://localhost:$port!" -ForegroundColor Green
        exit 0
    }
    Start-Sleep -Milliseconds 500
}

Write-Host "[9Router] Supervised processes spawned. Check status with: 9r status" -ForegroundColor Yellow
exit 0
