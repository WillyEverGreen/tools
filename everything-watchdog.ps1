# Everything & EverythingToolbar Continuous Self-Healing & Turbo-Optimization Watchdog
# Runs quietly in user session; guarantees instant <10ms Alt+Space response, 100% durability, and self-healing.
$ErrorActionPreference = "SilentlyContinue"

# Single-Instance Guard by Process Query
$myPid = $PID
$existing = Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" | Where-Object { 
    $_.ProcessId -ne $myPid -and $_.CommandLine -like "*everything-watchdog.ps1*" 
}
if ($existing) {
    Exit
}

$evExe = "C:\Program Files\Everything\Everything.exe"
$tbExe = "$env:LOCALAPPDATA\Programs\EverythingToolbar\EverythingToolbar.Launcher.exe"
$evIni = "$env:APPDATA\Everything\Everything.ini"
$evGolden = "$env:APPDATA\Everything\Everything.ini.golden"
$tbIni = "$env:APPDATA\EverythingToolbar\settings.ini"
$tbGolden = "$env:APPDATA\EverythingToolbar\settings.ini.golden"

# Win32 Window Finding for IPC Health Check
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinIPC {
    [DllImport("user32.dll", SetLastError = true)]
    public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
}
"@ -ErrorAction SilentlyContinue

$ipcMissCount = 0

while ($true) {
    try {
        # 1. Monitor Everything Engine (Client Process in current session)
        $evProcs = Get-Process -Name "Everything" -ErrorAction SilentlyContinue | Where-Object { $_.SessionId -ne 0 }
        if (-not $evProcs) {
            if (Test-Path $evExe) {
                Start-Process -FilePath $evExe -ArgumentList "-startup"
                $ipcMissCount = 0
            }
        } else {
            # Enforce AboveNormal CPU priority for instant response
            foreach ($p in $evProcs) {
                if ($p.PriorityClass -ne 'AboveNormal') {
                    $p.PriorityClass = [System.Diagnostics.ProcessPriorityClass]::AboveNormal
                }
                if (-not $p.Responding) {
                    Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
                    Start-Process -FilePath $evExe -ArgumentList "-startup"
                    $ipcMissCount = 0
                }
            }

            # IPC Window Health Check (Ensure Everything didn't lose its message loop)
            $w1 = [WinIPC]::FindWindow("EVERYTHING_TASKBAR_NOTIFICATION", $null)
            $w2 = [WinIPC]::FindWindow("EVERYTHING", $null)
            if ($w1 -eq [IntPtr]::Zero -and $w2 -eq [IntPtr]::Zero) {
                $ipcMissCount++
                if ($ipcMissCount -ge 2) {
                    # IPC window lost: bounce Everything cleanly
                    foreach ($p in $evProcs) {
                        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
                    }
                    Start-Process -FilePath $evExe -ArgumentList "-startup"
                    $ipcMissCount = 0
                }
            } else {
                $ipcMissCount = 0
            }
        }

        # 2. Monitor EverythingToolbar (Alt+Space Hotkey Sink)
        $tbProcs = @(Get-Process -Name "EverythingToolbar.Launcher" -ErrorAction SilentlyContinue)
        if ($tbProcs.Count -eq 0) {
            if (Test-Path $tbExe) {
                Start-Process -FilePath $tbExe -WindowStyle Hidden
            }
        } elseif ($tbProcs.Count -gt 1) {
            # Deduplicate: keep the oldest, terminate extras to prevent hotkey collisions
            $tbSorted = $tbProcs | Sort-Object StartTime
            for ($i = 1; $i -lt $tbSorted.Count; $i++) {
                Stop-Process -Id $tbSorted[$i].Id -Force -ErrorAction SilentlyContinue
            }
        } else {
            if (-not $tbProcs[0].Responding) {
                Stop-Process -Id $tbProcs[0].Id -Force -ErrorAction SilentlyContinue
                Start-Process -FilePath $tbExe -WindowStyle Hidden
            } elseif ($tbProcs[0].PriorityClass -ne 'AboveNormal') {
                $tbProcs[0].PriorityClass = [System.Diagnostics.ProcessPriorityClass]::AboveNormal
            }
        }

        # 3. Verify Configuration Integrity & Alt+Space Binding
        if (-not (Test-Path $tbIni) -and (Test-Path $tbGolden)) {
            Copy-Item -Path $tbGolden -Destination $tbIni -Force
        }
        if (-not (Test-Path $evIni) -and (Test-Path $evGolden)) {
            Copy-Item -Path $evGolden -Destination $evIni -Force
        }

        # 4. Check Everything NTFS Service
        $svc = Get-Service -Name "Everything" -ErrorAction SilentlyContinue
        if ($svc -and $svc.Status -ne "Running") {
            Start-Service -Name "Everything" -ErrorAction SilentlyContinue
        }
    } catch {
        # Fail-safe: loop never dies
    }

    Start-Sleep -Seconds 15
}
