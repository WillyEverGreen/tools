# Starts the installed 9router server directly in the background with continuous supervisor & watchdog.
# Same environment the launcher builds: PORT/HOSTNAME + NODE_PATH with the bundled and runtime node_modules.

$port = 20127
$pkg  = Join-Path $env:APPDATA 'npm\node_modules\9router'
$app  = Join-Path $pkg 'app'
$node = 'C:\Program Files\nodejs\node.exe'
$server = if (Test-Path (Join-Path $app 'custom-server.js')) { Join-Path $app 'custom-server.js' } else { Join-Path $app 'server.js' }
$supervisorScript = Join-Path $PSScriptRoot "9router-supervisor.ps1"
$watchdogScript = Join-Path $PSScriptRoot "9router-watchdog.ps1"

if (-not (Test-Path $server)) {
    Write-Host "[9Router] Not installed: $server (run: npm i -g 9router)" -ForegroundColor Red
    exit 1
}

# 1. Check if supervisor is running; if not, launch detached
$sup = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "9router-supervisor\.ps1" }
if (-not $sup -and (Test-Path $supervisorScript)) {
    $cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$supervisorScript`""
    Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = $cmd} | Out-Null
}

# 2. Check if watchdog is running; if not, launch detached
$wd = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "9router-watchdog\.ps1" }
if (-not $wd -and (Test-Path $watchdogScript)) {
    $cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$watchdogScript`""
    Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = $cmd} | Out-Null
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
