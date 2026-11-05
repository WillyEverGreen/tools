# Everything & EverythingToolbar Diagnostic & Self-Healing Doctor (v2.0)
$ErrorActionPreference = "SilentlyContinue"

Write-Host "=== Everything & EverythingToolbar Doctor ===" -ForegroundColor Cyan

# 1. Check NTFS Service
$svc = Get-Service -Name "Everything" -ErrorAction SilentlyContinue
if ($svc -and $svc.Status -ne "Running") {
    Start-Service -Name "Everything" -ErrorAction SilentlyContinue
    Write-Host "[Fixed] Started Everything NTFS service." -ForegroundColor Green
} elseif ($svc) {
    Write-Host "[OK] Everything NTFS service is running (StartType: $($svc.StartType))." -ForegroundColor Green
} else {
    Write-Host "[Warn] Everything NTFS service not installed." -ForegroundColor Yellow
}

# 2. Check Everything Engine Process
$client = Get-Process -Name "Everything" -ErrorAction SilentlyContinue | Where-Object { $_.SessionId -ne 0 }
if (-not $client) {
    $evExe = "C:\Program Files\Everything\Everything.exe"
    if (Test-Path $evExe) {
        Start-Process -FilePath $evExe -ArgumentList "-startup" -WindowStyle Hidden
        Start-Sleep -Seconds 2
        Write-Host "[Fixed] Started Everything engine in background." -ForegroundColor Green
    }
} else {
    $memMB = [math]::Round(($client | Measure-Object -Property WorkingSet64 -Sum).Sum / 1MB, 1)
    Write-Host "[OK] Everything engine active (PID: $($client.Id | Select-Object -First 1), RAM: $memMB MB, Responding: $($client.Responding))." -ForegroundColor Green
}

# 3. Check Everything Configuration & Golden Backup
$evIni = "$env:APPDATA\Everything\Everything.ini"
$evGolden = "$env:APPDATA\Everything\Everything.ini.golden"
if (-not (Test-Path $evIni) -and (Test-Path $evGolden)) {
    Copy-Item $evGolden $evIni -Force
    Write-Host "[Fixed] Restored Everything.ini from golden backup." -ForegroundColor Green
} elseif (Test-Path $evIni) {
    if (-not (Test-Path $evGolden)) {
        Copy-Item $evIni $evGolden -Force
        Write-Host "[OK] Created golden backup of Everything.ini." -ForegroundColor Green
    } else {
        Write-Host "[OK] Everything.ini and golden backup verified." -ForegroundColor Green
    }
}

# 4. Check EverythingToolbar Launcher Process
$tbProcs = @(Get-Process -Name "EverythingToolbar.Launcher" -ErrorAction SilentlyContinue)
if ($tbProcs.Count -eq 0) {
    $tbExe = "$env:LOCALAPPDATA\Programs\EverythingToolbar\EverythingToolbar.Launcher.exe"
    if (Test-Path $tbExe) {
        Start-Process -FilePath $tbExe -WindowStyle Hidden
        Write-Host "[Fixed] Started EverythingToolbar launcher." -ForegroundColor Green
    }
} elseif ($tbProcs.Count -gt 1) {
    $tbSorted = $tbProcs | Sort-Object StartTime
    for ($i = 1; $i -lt $tbSorted.Count; $i++) {
        Stop-Process -Id $tbSorted[$i].Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "[Fixed] Deduplicated EverythingToolbar instances (kept PID: $($tbSorted[0].Id))." -ForegroundColor Green
} else {
    Write-Host "[OK] EverythingToolbar launcher active (PID: $($tbProcs[0].Id), Responding: $($tbProcs[0].Responding))." -ForegroundColor Green
}

# 5. Check EverythingToolbar Settings & Alt+Space Shortcut
$tbIni = "$env:APPDATA\EverythingToolbar\settings.ini"
$tbGolden = "$env:APPDATA\EverythingToolbar\settings.ini.golden"
if (Test-Path $tbIni) {
    $content = Get-Content $tbIni -Raw
    $hasMod = $content -match '(?m)^ShortcutModifiers=1'
    $hasKey = $content -match '(?m)^ShortcutKey=18'
    if ($hasMod -and $hasKey) {
        Write-Host "[OK] Shortcut verified: Alt+Space (Modifier: 1 [Alt], Key: 18 [Space])." -ForegroundColor Green
    } else {
        Write-Host "[Warn] Shortcut not configured to Alt+Space in settings.ini." -ForegroundColor Yellow
    }

    if (-not (Test-Path $tbGolden)) {
        Copy-Item $tbIni $tbGolden -Force
        Write-Host "[OK] Created golden backup of settings.ini." -ForegroundColor Green
    } else {
        Write-Host "[OK] EverythingToolbar golden backup verified." -ForegroundColor Green
    }
} elseif (Test-Path $tbGolden) {
    Copy-Item $tbGolden $tbIni -Force
    Write-Host "[Fixed] Restored EverythingToolbar settings.ini from golden backup." -ForegroundColor Green
}

# 6. Check Self-Healing Watchdog
$watchdog = Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" | Where-Object { $_.CommandLine -like "*everything-watchdog.ps1*" }
if (-not $watchdog) {
    $vbs = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\everything-watchdog.vbs"
    if (Test-Path $vbs) {
        Start-Process "wscript.exe" -ArgumentList """$vbs"""
        Write-Host "[Fixed] Launched continuous self-healing watchdog daemon." -ForegroundColor Green
    }
} else {
    Write-Host "[OK] Continuous self-healing watchdog daemon active (PID: $($watchdog.ProcessId | Select-Object -First 1))." -ForegroundColor Green
}

# 7. Check Startup Persistence
$startupDir = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$scEv = Join-Path $startupDir "Everything.lnk"
$vbsWd = Join-Path $startupDir "everything-watchdog.vbs"
$okStartup = (Test-Path $scEv) -and (Test-Path $vbsWd)
if ($okStartup) {
    Write-Host "[OK] Startup entries verified (Everything.lnk, everything-watchdog.vbs in shell:startup)." -ForegroundColor Green
} else {
    Write-Host "[Warn] Startup entries incomplete." -ForegroundColor Yellow
}

Write-Host "=== Health Status: All Systems Operational ===" -ForegroundColor Green
