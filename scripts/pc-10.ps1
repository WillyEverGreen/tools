<#
  pc-10.ps1 - one-time setup that takes this PC to its best sustainable state.
  Run it yourself; it asks for admin rights (UAC) and changes nothing outside the list below.

    1. Turns on the weekly upkeep task        (runs C:\tools\pc-care.ps1 every Sunday 13:00, or at next start)
    2. Clears old temp files                  (user Temp and C:\Windows\Temp, files older than 7 days)
    3. Hardens Windows Defender               (blocks potentially unwanted apps, network protection, fresh signatures)
    4. Trims the SSD                          (Optimize-Volume -ReTrim, safe and built in)
    5. Checks Windows Update                  (starts a scan)
    6. Reports BitLocker / Secure Boot / TPM  (checks only; it does NOT turn encryption on for you)
    7. Saves a battery report and health      (C:\tools\_logs\battery-report.html)
    8. Runs the health check and shows the result

  Usage:   powershell -ExecutionPolicy Bypass -File C:\tools\pc-10.ps1
           add -DryRun to see what it would do without changing anything
  Undo:    Unregister-ScheduledTask -TaskName 'PC-Care Weekly' -Confirm:$false
           Set-MpPreference -PUAProtection Disabled        (only if a wanted app gets blocked)
#>
param([switch]$DryRun)

# ---------- elevate ----------
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
  Write-Host 'Needs admin rights. Approve the UAC prompt...' -ForegroundColor Yellow
  $argList = '-NoProfile -ExecutionPolicy Bypass -File "' + $PSCommandPath + '"' + $(if ($DryRun) { ' -DryRun' } else { '' })
  Start-Process powershell.exe -Verb RunAs -ArgumentList $argList
  exit
}

$logDir = 'C:\tools\_logs'
New-Item -ItemType Directory -Force $logDir | Out-Null
Start-Transcript -Path (Join-Path $logDir ('pc-10-' + (Get-Date -Format 'yyyyMMdd-HHmm') + '.log')) | Out-Null
$results = [ordered]@{}
function Step($name, [scriptblock]$do) {
  Write-Host "`n== $name" -ForegroundColor Cyan
  try {
    if ($DryRun) { Write-Host '   (dry run: skipped)'; $results[$name] = 'dry run'; return }
    & $do
    $results[$name] = 'done'
  } catch {
    Write-Host "   FAILED: $($_.Exception.Message)" -ForegroundColor Red
    $results[$name] = 'FAILED'
  }
}
function GB($b) { [math]::Round($b / 1GB, 1) }

$freeBefore = (Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'").FreeSpace

# ---------- 1. weekly upkeep ----------
Step '1. Weekly upkeep task' {
  if (-not (Test-Path 'C:\tools\pc-care.ps1')) { throw 'C:\tools\pc-care.ps1 is missing' }
  $user = (Get-CimInstance Win32_ComputerSystem).UserName
  $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\tools\pc-care.ps1"'
  $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 1pm
  $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 1)
  $principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
  Register-ScheduledTask -TaskName 'PC-Care Weekly' -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Weekly temp cleanup and health check (C:\tools\pc-care.ps1)' -Force | Out-Null
  Write-Host "   registered for $user, next run: $((Get-ScheduledTask 'PC-Care Weekly' | Get-ScheduledTaskInfo).NextRunTime)"
}

# ---------- 2. temp cleanup ----------
Step '2. Old temp files (older than 7 days)' {
  $cutoff = (Get-Date).AddDays(-7)
  $freed = 0
  foreach ($dir in @($env:TEMP, 'C:\Windows\Temp') | Select-Object -Unique) {
    Get-ChildItem -LiteralPath $dir -Recurse -Force -File -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -lt $cutoff } | ForEach-Object {
      $len = $_.Length
      # -LiteralPath: some temp folders have [brackets] in their names, which -Path treats as wildcards.
      Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
      if (-not (Test-Path -LiteralPath $_.FullName)) { $freed += $len }
    }
    Get-ChildItem -LiteralPath $dir -Recurse -Force -Directory -ErrorAction SilentlyContinue | Sort-Object { $_.FullName.Length } -Descending |
      Where-Object { -not (Get-ChildItem -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue) } | ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue }
  }
  Write-Host "   freed $(GB $freed) GB"
}

# ---------- 3. Defender ----------
Step '3. Windows Defender hardening' {
  Update-MpSignature -ErrorAction SilentlyContinue
  Set-MpPreference -PUAProtection Enabled
  Set-MpPreference -EnableNetworkProtection Enabled
  Set-MpPreference -DisableRealtimeMonitoring $false
  $p = Get-MpPreference
  Write-Host "   PUA protection: $($p.PUAProtection)  Network protection: $($p.EnableNetworkProtection)  Real-time off: $($p.DisableRealtimeMonitoring)"
}

# ---------- 4. SSD trim ----------
Step '4. SSD trim' {
  foreach ($v in Get-Volume | Where-Object { $_.DriveType -eq 'Fixed' -and $_.DriveLetter -and $_.FileSystem -eq 'NTFS' }) {
    Optimize-Volume -DriveLetter $v.DriveLetter -ReTrim -ErrorAction SilentlyContinue
    Write-Host "   trimmed $($v.DriveLetter):"
  }
}

# ---------- 5. Windows Update ----------
Step '5. Windows Update scan' {
  Start-Process -FilePath "$env:SystemRoot\System32\UsoClient.exe" -ArgumentList 'StartScan' -WindowStyle Hidden
  Write-Host '   scan started; check Settings > Windows Update for anything pending'
}

# ---------- 6. encryption and boot security (check only) ----------
Step '6. BitLocker / Secure Boot / TPM' {
  try { Write-Host "   Secure Boot: $(Confirm-SecureBootUEFI)" } catch { Write-Host '   Secure Boot: not supported or not enabled in firmware' -ForegroundColor Yellow }
  $tpm = Get-Tpm
  Write-Host "   TPM present: $($tpm.TpmPresent)  ready: $($tpm.TpmReady)"
  $bl = Get-BitLockerVolume -MountPoint 'C:' -ErrorAction SilentlyContinue
  if ($bl) { Write-Host "   BitLocker C: $($bl.ProtectionStatus) ($($bl.VolumeStatus))" }
  else { Write-Host '   BitLocker cmdlets unavailable (Windows Home). Check Settings > Privacy & security > Device encryption.' -ForegroundColor Yellow }
  if (-not $bl -or $bl.ProtectionStatus -ne 'On') {
    Write-Host '   To encrypt: Settings > Privacy & security > Device encryption > On. Save the recovery key to your Microsoft account first.' -ForegroundColor Yellow
  }
}

# ---------- 7. battery ----------
Step '7. Battery report' {
  $html = Join-Path $logDir 'battery-report.html'
  $xml = Join-Path $logDir 'battery-report.xml'
  powercfg /batteryreport /output $html | Out-Null
  powercfg /batteryreport /output $xml /xml | Out-Null
  [xml]$x = Get-Content $xml
  $b = @($x.BatteryReport.Batteries.Battery)[0]
  $design = [double]$b.DesignCapacity; $full = [double]$b.FullChargeCapacity
  Write-Host ("   health {0}% (design {1:N0} mWh, now {2:N0} mWh). Report: {3}" -f [math]::Round(100 * $full / $design), $design, $full, $html)
}

# ---------- 8. health check ----------
Step '8. Health check' {
  & 'C:\tools\pc-care.ps1' -Check -Quiet
}

$freeAfter = (Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'").FreeSpace
Write-Host "`n================ SUMMARY ================" -ForegroundColor Green
$results.GetEnumerator() | ForEach-Object { Write-Host ('{0,-45} {1}' -f $_.Key, $_.Value) }
Write-Host ("C: free space: {0} GB -> {1} GB" -f (GB $freeBefore), (GB $freeAfter))
Write-Host 'Still manual: turn on Device encryption (step 6) and restart once if Windows asks.' -ForegroundColor Yellow
Stop-Transcript | Out-Null
Read-Host 'Press Enter to close'
