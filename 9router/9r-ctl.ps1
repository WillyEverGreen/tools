# 9r-ctl.ps1 — control the 9Router keep-alive stack (scheduled task "9Router").
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File C:\tools\9router\9r-ctl.ps1 status|start|stop|restart
#
# Stopping relies on the supervisor's loopback control channel (port 20129), NOT
# on killing processes: when the task runs as S4U the processes live in session 0
# and a normal shell gets "Access is denied" from Stop-Process, while
# `schtasks /End` reports success without tearing the tree down.
$ErrorActionPreference = "Continue"

$TaskName    = "9Router"
$Port        = 20127
$BridgePort  = 20128
$ControlPort = 20129
$HealthUrl   = "http://127.0.0.1:$Port/api/health"
$ControlUrl  = "http://127.0.0.1:$ControlPort"
$StopFlag    = "C:\tools\9router\stopped.flag"

function Get-TaskState {
    $out = & schtasks.exe /Query /TN $TaskName /FO LIST 2>$null
    if ($LASTEXITCODE -ne 0) { return "Missing" }
    $line = $out | Where-Object { $_ -match "^Status\s*:" } | Select-Object -First 1
    if ($line) { return ($line -split ":", 2)[1].Trim() }
    return "Unknown"
}

function Get-ControlPing {
    try {
        $r = Invoke-WebRequest -Uri "$ControlUrl/ping" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        return ($r.Content | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Get-SupervisorPid {
    $ping = Get-ControlPing
    if ($ping -and $ping.pid) { return [int]$ping.pid }
    $lock = "C:\tools\9router\supervisor.lock"
    if (Test-Path $lock) {
        $raw = (Get-Content $lock -ErrorAction SilentlyContinue | Select-Object -First 1)
        if ($raw -match '^\d+$') {
            $proc = Get-Process -Id ([int]$raw) -ErrorAction SilentlyContinue
            if ($proc -and $proc.ProcessName -eq "node") { return [int]$raw }
        }
    }
    return 0
}

function Get-ServerPid {
    $ping = Get-ControlPing
    if ($ping -and $ping.child) { return [int]$ping.child }
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($conn) { return $conn.OwningProcess }
    return 0
}

function Test-Health([string]$url) {
    try {
        $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 6 -ErrorAction Stop
        return $resp.StatusCode
    } catch {
        return 0
    }
}

function Wait-PortsFree([int]$seconds) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        if (-not (Get-NetTCPConnection -LocalPort $Port, $BridgePort -State Listen -ErrorAction SilentlyContinue)) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Show-Status {
    $state   = Get-TaskState
    $ping    = Get-ControlPing
    $sup     = Get-SupervisorPid
    $srv     = Get-ServerPid
    $h1      = Test-Health $HealthUrl
    $h2      = Test-Health "http://127.0.0.1:$BridgePort/api/health"

    Write-Host ""
    Write-Host "  9Router" -ForegroundColor Cyan
    Write-Host "  ------------------------------------------------------------"
    $stateColor = if ($state -eq "Running") { "Green" } elseif ($state -eq "Disabled") { "Yellow" } else { "Red" }
    Write-Host ("  Task '{0}'      : " -f $TaskName) -NoNewline; Write-Host $state -ForegroundColor $stateColor

    if ($sup -gt 0) {
        $p = Get-Process -Id $sup -ErrorAction SilentlyContinue
        $ram = if ($p) { [math]::Round($p.WorkingSet64 / 1MB, 1) } else { 0 }
        $managed = if ($ping) { "managed (control :$ControlPort)" } else { "NOT managed (no control channel)" }
        Write-Host ("  Supervisor       : pid {0}  ({1} MB, {2})" -f $sup, $ram, $managed)
    } else {
        Write-Host "  Supervisor       : not running" -ForegroundColor Red
    }

    if ($srv -gt 0) {
        $p = Get-Process -Id $srv -ErrorAction SilentlyContinue
        $ram = if ($p) { [math]::Round($p.WorkingSet64 / 1MB, 1) } else { 0 }
        $up = "?"
        if ($ping -and $ping.uptimeSec) {
            $h = [math]::Round($ping.uptimeSec / 3600, 1)
            $m = [math]::Round($ping.uptimeSec / 60, 0)
            $up = if ($h -ge 1) { "${h}h" } else { "${m}m" }
        } elseif ($p) {
            try { $up = [string][math]::Round(((Get-Date) - $p.StartTime).TotalHours, 1) + "h" } catch {}
        }
        Write-Host ("  Gateway/server   : pid {0}  ({1} MB, up {2})" -f $srv, $ram, $up)
    } else {
        Write-Host "  Gateway/server   : not listening on $Port" -ForegroundColor Red
    }

    $c1 = if ($h1 -eq 200) { "Green" } else { "Red" }
    $c2 = if ($h2 -eq 200) { "Green" } else { "Red" }
    Write-Host "  http://localhost:$Port/api/health  : " -NoNewline; Write-Host $h1 -ForegroundColor $c1
    Write-Host "  http://localhost:$BridgePort/api/health  : " -NoNewline; Write-Host $h2 -ForegroundColor $c2
    Write-Host "  Dashboard        : http://localhost:$Port/dashboard"
    Write-Host "  Logs             : C:\tools\9router\logs\"
    Write-Host ""
}

function Start-NineRouter {
    if (Test-Path $StopFlag) {
        Remove-Item -Path $StopFlag -Force -ErrorAction SilentlyContinue
    }

    # If a supervisor is running but is NOT the task-managed one (no control
    # channel, or the task is not Running), ask it to go away first so the task
    # starts a clean instance. A control-channel supervisor stops itself cleanly.
    if ((Get-SupervisorPid) -gt 0 -and (Get-TaskState) -ne "Running") {
        $ping = Get-ControlPing
        if ($ping) {
            try { Invoke-WebRequest -Method POST -Uri "$ControlUrl/stop" -UseBasicParsing -TimeoutSec 6 -ErrorAction Stop | Out-Null } catch {}
            if (-not (Wait-PortsFree 10)) {
                Write-Host "[9Router] A running instance could not be stopped. Run '9router-repair' once (UAC) or reboot." -ForegroundColor Yellow
            }
        } else {
            Write-Host "[9Router] A running instance has no control channel (older build)." -ForegroundColor Yellow
            Write-Host "[9Router] Run '9router-repair' once (UAC) to replace it, or reboot." -ForegroundColor Yellow
        }
    }

    & schtasks.exe /Run /TN $TaskName 2>&1 | Out-Null
    Write-Host "[9Router] Start requested." -ForegroundColor Green
    for ($i = 0; $i -lt 30; $i++) {
        if ((Test-Health $HealthUrl) -eq 200) {
            Write-Host "[9Router] Ready on http://localhost:$Port (dashboard: /dashboard)" -ForegroundColor Green
            return
        }
        Start-Sleep -Milliseconds 1000
    }
    Write-Host "[9Router] Not healthy yet - check C:\tools\9router\logs\supervisor.log" -ForegroundColor Yellow
}

function Stop-NineRouter {
    # Set durable stop-flag so supervisor stays stopped across minute watchdogs
    Set-Content -Path $StopFlag -Value "stopped at $(Get-Date)" -Force -ErrorAction SilentlyContinue

    $ping = Get-ControlPing
    if ($ping) {
        try { Invoke-WebRequest -Method POST -Uri "$ControlUrl/stop" -UseBasicParsing -TimeoutSec 6 -ErrorAction Stop | Out-Null } catch {}
        if (Wait-PortsFree 12) {
            Write-Host "[9Router] Stopped (run '9r start' to bring it back)." -ForegroundColor Yellow
            return
        }
    }

    # Fallback for instances without a control channel.
    & schtasks.exe /End /TN $TaskName 2>&1 | Out-Null
    Start-Sleep -Milliseconds 1500
    foreach ($target in @((Get-SupervisorPid), (Get-ServerPid))) {
        if ($target -gt 0) {
            $name = (Get-Process -Id $target -ErrorAction SilentlyContinue).ProcessName
            if ($name -eq "node") {
                try { Stop-Process -Id $target -Force -ErrorAction Stop; Write-Host "[9Router] stopped pid $target" -ForegroundColor Yellow } catch {}
            }
        }
    }
    if (Wait-PortsFree 5) {
        Write-Host "[9Router] Stopped (task disabled - run '9r start' to bring it back)." -ForegroundColor Yellow
    } else {
        Write-Host "[9Router] Still running (session-0 process, needs elevation). Run '9router-repair' once (UAC) or reboot." -ForegroundColor Yellow
    }
}

switch ($args[0]) {
    "start"   { Start-NineRouter }
    "stop"    { Stop-NineRouter }
    "restart" { Stop-NineRouter; Start-Sleep -Seconds 1; Start-NineRouter }
    "status"  { Show-Status }
    default   { Show-Status }
}
