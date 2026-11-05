# Starts the installed 9router server directly (no launcher process) in the background.
# Same environment the launcher builds: PORT/HOSTNAME + NODE_PATH with the bundled and runtime node_modules.
$port = 20127
$pkg  = Join-Path $env:APPDATA 'npm\node_modules\9router'
$app  = Join-Path $pkg 'app'
$node = 'C:\Program Files\nodejs\node.exe'
$server = if (Test-Path (Join-Path $app 'custom-server.js')) { Join-Path $app 'custom-server.js' } else { Join-Path $app 'server.js' }

if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
    Write-Host "[9Router] Already running on port $port!" -ForegroundColor Green
    exit 0
}
if (-not (Test-Path $server)) {
    Write-Host "[9Router] Not installed: $server (run: npm i -g 9router)" -ForegroundColor Red
    exit 1
}

$runtimeNm = Join-Path $env:APPDATA '9router\runtime\node_modules'
$env:NODE_PATH = (@($runtimeNm, (Join-Path $app 'node_modules'), $env:NODE_PATH) | Where-Object { $_ }) -join ';'
$env:PORT = "$port"
$env:HOSTNAME = '0.0.0.0'

Write-Host "[9Router] Starting in background on port $port..." -ForegroundColor Cyan
Start-Process -FilePath $node -WorkingDirectory $app -WindowStyle Hidden `
    -ArgumentList @('--dns-result-order=ipv4first', '--max-old-space-size=1024', $server)

$bridgeScript = "d:\EXPERIMENTS PROJECTS\9router\scripts\proxy-20128.js"
if (Test-Path $bridgeScript) {
    Start-Process -FilePath $node -ArgumentList @($bridgeScript) -WindowStyle Hidden
}

for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 500
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        Write-Host "[9Router] Ready on http://localhost:$port!" -ForegroundColor Green
        exit 0
    }
}
Write-Host '[9Router] Still starting - check again with: 9r status' -ForegroundColor Yellow
exit 0
