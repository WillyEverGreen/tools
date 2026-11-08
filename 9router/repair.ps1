# repair.ps1 — elevated: kill any orphaned 9Router processes and restart the task.
#
# Only needed for the transition from the previous (pre-control-channel) build,
# or if a supervisor is ever left running that `9r stop` cannot reach. Run it via
# the UAC wrapper:  C:\tools\9router\repair.cmd  (or `9router-repair`).
$ErrorActionPreference = "Continue"

$killed = @()

foreach ($proc in (Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue)) {
    if ($proc.CommandLine -and ($proc.CommandLine -match "supervisor\.cjs" -or $proc.CommandLine -match "9router\\app\\(custom-server|server)\.js")) {
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
        $killed += $proc.ProcessId
    }
}
foreach ($proc in (Get-CimInstance Win32_Process -Filter "Name='wscript.exe'" -ErrorAction SilentlyContinue)) {
    if ($proc.CommandLine -and $proc.CommandLine -match "launch-supervisor\.vbs") {
        Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
        $killed += $proc.ProcessId
    }
}

Remove-Item 'C:\tools\9router\supervisor.lock' -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 800

# Anything still holding the two ports is ours to clear.
foreach ($conn in (Get-NetTCPConnection -LocalPort 20127, 20128 -State Listen -ErrorAction SilentlyContinue)) {
    if ($conn.OwningProcess -gt 0) {
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        $killed += $conn.OwningProcess
    }
}

Write-Output ("killed: " + ((@($killed) | Select-Object -Unique) -join ", "))

& schtasks.exe /Change /TN "9Router" /ENABLE 2>&1 | Out-Null
& schtasks.exe /Run /TN "9Router" 2>&1 | Out-Null
Write-Output "task start requested"
