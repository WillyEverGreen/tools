# 9router-supervisor.ps1
# Continuous High-Reliability Process Supervisor for 9Router daemon & proxy bridge
$ErrorActionPreference = "SilentlyContinue"

# Single-Instance Guard
$myPid = $PID
$supPattern = '-File\s+["'']?[^"'']*9router-supervisor\.ps1'
$existing = Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" | Where-Object { 
    $_.ProcessId -ne $myPid -and $_.CommandLine -match $supPattern 
}
if ($existing) {
    Exit
}

$port = 20127
$bridgePort = 20128
$node = if (Test-Path 'C:\Program Files\nodejs\node.exe') { 'C:\Program Files\nodejs\node.exe' } else { (Get-Command node.exe -ErrorAction SilentlyContinue).Source }
$pkg  = Join-Path $env:APPDATA 'npm\node_modules\9router'
$app  = Join-Path $pkg 'app'
$server = if (Test-Path (Join-Path $app 'custom-server.js')) { Join-Path $app 'custom-server.js' } else { Join-Path $app 'server.js' }
$bridgeScript = Join-Path $PSScriptRoot "proxy-20128.js"
if (-not (Test-Path $bridgeScript)) {
    $bridgeScript = "d:\EXPERIMENTS PROJECTS\9router\scripts\proxy-20128.js"
}

if (-not (Test-Path $server)) {
    Exit
}

$runtimeNm = Join-Path $env:APPDATA '9router\runtime\node_modules'
$env:NODE_PATH = (@($runtimeNm, (Join-Path $app 'node_modules'), $env:NODE_PATH) | Where-Object { $_ }) -join ';'
$env:PORT = "$port"
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
    try {
        # 1. Server process check
        $serverRunning = $false
        if ($serverProc -and -not $serverProc.HasExited) {
            $serverRunning = $true
        } else {
            $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
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
            $bConn = Get-NetTCPConnection -LocalPort $bridgePort -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
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
            $resp = curl.exe -s --max-time 3 "http://127.0.0.1:$port/api/health"
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
        }
    } catch {
        # Keep loop alive under all circumstances
    }

    Start-Sleep -Seconds 3
}
