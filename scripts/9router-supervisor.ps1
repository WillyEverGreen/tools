# 9router-supervisor.ps1
# High-reliability process supervisor for 9Router daemon & local proxy bridge.
# Checks process existence & active HTTP health every 3 seconds.
# Restarts dead or unresponsive instances within 3 seconds.

param(
    [int]$Port = 20127,
    [int]$BridgePort = 20128
)

$ErrorActionPreference = 'SilentlyContinue'

$node = 'C:\Program Files\nodejs\node.exe'
$pkg  = Join-Path $env:APPDATA 'npm\node_modules\9router'
$app  = Join-Path $pkg 'app'
$server = if (Test-Path (Join-Path $app 'custom-server.js')) { Join-Path $app 'custom-server.js' } else { Join-Path $app 'server.js' }
$bridgeScript = "d:\EXPERIMENTS PROJECTS\9router\scripts\proxy-20128.js"

if (-not (Test-Path $server)) {
    exit 1
}

$runtimeNm = Join-Path $env:APPDATA '9router\runtime\node_modules'
$env:NODE_PATH = (@($runtimeNm, (Join-Path $app 'node_modules'), $env:NODE_PATH) | Where-Object { $_ }) -join ';'
$env:PORT = "$Port"
$env:HOSTNAME = '0.0.0.0'

function Start-ServerProcess {
    return Start-Process -FilePath $node -WorkingDirectory $app -WindowStyle Hidden `
        -ArgumentList @('--dns-result-order=ipv4first', '--max-old-space-size=1024', $server) `
        -PassThru
}

function Start-BridgeProcess {
    if (Test-Path $bridgeScript) {
        return Start-Process -FilePath $node -WorkingDirectory (Split-Path $bridgeScript) -WindowStyle Hidden `
            -ArgumentList @($bridgeScript) `
            -PassThru
    }
    return $null
}

$serverProc = $null
$bridgeProc = $null
$consecutiveFailures = 0
$lastStartTime = [DateTime]::MinValue

while ($true) {
    # 1. Server process check
    $serverRunning = $false
    if ($serverProc -and -not $serverProc.HasExited) {
        $serverRunning = $true
    } else {
        $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($conn -and $conn.OwningProcess -gt 0) {
            $serverProc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
            $serverRunning = ($serverProc -ne $null -and -not $serverProc.HasExited)
        }
    }

    if (-not $serverRunning) {
        $serverProc = Start-ServerProcess
        $lastStartTime = [DateTime]::UtcNow
        $consecutiveFailures = 0
        Start-Sleep -Seconds 2
    }

    # 2. Bridge process check
    $bridgeRunning = $false
    if ($bridgeProc -and -not $bridgeProc.HasExited) {
        $bridgeRunning = $true
    } else {
        $bConn = Get-NetTCPConnection -LocalPort $BridgePort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($bConn -and $bConn.OwningProcess -gt 0) {
            $bridgeProc = Get-Process -Id $bConn.OwningProcess -ErrorAction SilentlyContinue
            $bridgeRunning = ($bridgeProc -ne $null -and -not $bridgeProc.HasExited)
        }
    }

    if (-not $bridgeRunning) {
        $bridgeProc = Start-BridgeProcess
    }

    # 3. HTTP health probe (allow 15s warm-up; recycle only after 3 consecutive deadlocks)
    $elapsedWarmup = ([DateTime]::UtcNow - $lastStartTime).TotalSeconds
    if ($elapsedWarmup -gt 15) {
        try {
            $resp = curl.exe -s --max-time 3 "http://127.0.0.1:$Port/api/health"
            if ($resp -match 'ok') {
                $consecutiveFailures = 0
            } else {
                $consecutiveFailures++
                if ($consecutiveFailures -ge 3) {
                    if ($serverProc -and -not $serverProc.HasExited) {
                        Stop-Process -Id $serverProc.Id -Force -ErrorAction SilentlyContinue
                    }
                    $consecutiveFailures = 0
                }
            }
        } catch {
            $consecutiveFailures++
        }
    }

    Start-Sleep -Seconds 3
}
