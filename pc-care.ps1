<#
  pc-care.ps1 - weekly upkeep and health watch for this PC. Runs without admin rights.

  What it does (safe, nothing it removes is irreplaceable):
    1. Deletes files in %TEMP% older than 7 days (skips anything in use).
    2. Prunes the uv download cache and verifies the npm cache.
    3. Checks health and writes C:\tools\_logs\pc-health.txt and pc-health.json.
    4. Shows one Windows notification only when something needs attention.

  Usage:   pc-care            run upkeep + health check
           pc-care -Check     health check only (no cleanup)
           pc-care -Quiet     no notification
  Undo:    Unregister-ScheduledTask -TaskName 'PC-Care Weekly' -Confirm:$false
#>
param([switch]$Check, [switch]$Quiet, [switch]$Full)

$ErrorActionPreference = 'SilentlyContinue'
$logDir = 'C:\tools\_logs'
New-Item -ItemType Directory -Force $logDir | Out-Null
$issues = New-Object System.Collections.Generic.List[string]
$info = [ordered]@{ time = (Get-Date).ToString('s') }

# ---------- 1. upkeep ----------
$freed = 0
if (-not $Check) {
  $cutoff = (Get-Date).AddDays(-7)
  # -LiteralPath everywhere: some temp folders have [brackets] in their names (wildcards for -Path).
  Get-ChildItem -LiteralPath $env:TEMP -Recurse -Force -File | Where-Object { $_.LastWriteTime -lt $cutoff } | ForEach-Object {
    $len = $_.Length
    Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue
    if (-not (Test-Path -LiteralPath $_.FullName)) { $freed += $len }
  }
  # remove now-empty folders (deepest first)
  Get-ChildItem -LiteralPath $env:TEMP -Recurse -Force -Directory | Sort-Object { $_.FullName.Length } -Descending | Where-Object { -not (Get-ChildItem -LiteralPath $_.FullName -Force) } | ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue }
  if (Test-Path 'C:\tools\uv.exe') { & 'C:\tools\uv.exe' cache prune 2>&1 | Out-Null }
  if (Get-Command npm -ErrorAction SilentlyContinue) { npm cache verify 2>&1 | Out-Null }
}
$info.tempFreedMB = [math]::Round($freed / 1MB)

# ---------- 2. health ----------
# Disk space (warn below 15% free)
$info.disks = @()
Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | ForEach-Object {
  $pct = [math]::Round(100 * $_.FreeSpace / $_.Size)
  $info.disks += [ordered]@{ drive = $_.DeviceID; freeGB = [math]::Round($_.FreeSpace / 1GB); percentFree = $pct }
  if ($pct -lt 15) { $issues.Add("Drive $($_.DeviceID) is $pct% free ($([math]::Round($_.FreeSpace / 1GB)) GB). Free some space.") }
}

# SSD health
Get-PhysicalDisk | ForEach-Object {
  if ($_.HealthStatus -ne 'Healthy') { $issues.Add("Disk $($_.FriendlyName) reports $($_.HealthStatus). Back up now.") }
  $info.diskHealth = "$($_.FriendlyName): $($_.HealthStatus)"
}

# Antivirus and firewall
$mp = Get-MpComputerStatus
if ($mp) {
  $info.defender = [ordered]@{ realtime = $mp.RealTimeProtectionEnabled; signatureAgeDays = $mp.AntivirusSignatureAge }
  if (-not $mp.RealTimeProtectionEnabled) { $issues.Add('Windows Defender real-time protection is OFF.') }
  if ($mp.AntivirusSignatureAge -gt 3) { $issues.Add("Defender signatures are $($mp.AntivirusSignatureAge) days old. Check Windows Update.") }
}
Get-NetFirewallProfile | Where-Object { -not $_.Enabled } | ForEach-Object { $issues.Add("Firewall is OFF for the $($_.Name) profile.") }

# Battery wear (when Windows exposes it)
try {
  $full = (Get-CimInstance -Namespace root\wmi -ClassName BatteryFullChargedCapacity -ErrorAction Stop).FullChargedCapacity
  $design = (Get-CimInstance -Namespace root\wmi -ClassName BatteryStaticData -ErrorAction Stop).DesignedCapacity
  if ($design) {
    $health = [math]::Round(100 * $full / $design)
    $info.batteryHealthPercent = $health
    if ($health -lt 70) { $issues.Add("Battery health is $health% of its design capacity. Consider a replacement.") }
  }
} catch { }
# The WMI classes above often fail on laptops; powercfg's own report is reliable.
if (-not $info.Contains('batteryHealthPercent') -and (Get-CimInstance Win32_Battery)) {
  try {
    $xmlFile = Join-Path $logDir 'battery-report.xml'
    powercfg /batteryreport /output $xmlFile /xml | Out-Null
    [xml]$bx = Get-Content $xmlFile
    $bat = @($bx.BatteryReport.Batteries.Battery)[0]
    $health = [math]::Round(100 * [double]$bat.FullChargeCapacity / [double]$bat.DesignCapacity)
    $info.batteryHealthPercent = $health
    if ($health -lt 70) { $issues.Add("Battery health is $health% of its design capacity. Consider a replacement.") }
  } catch { }
}

# Pending reboot and uptime
$pending = (Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired') -or (Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending')
$up = ((Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime).Days
$info.uptimeDays = $up
if ($pending) { $issues.Add('Windows is waiting for a restart to finish updates.') }
elseif ($up -ge 14) { $issues.Add("The PC has been up $up days. A restart keeps it fast.") }

# Startup creep (baseline stored on first run)
# Only entries that are actually enabled count (Win32_StartupCommand also lists disabled ones).
function Get-EnabledStartup {
  $out = @()
  $sets = @(
    @{ Run = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'; Approved = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run'; Tag = 'user' },
    @{ Run = 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Run'; Approved = 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run'; Tag = 'machine' }
  )
  foreach ($s in $sets) {
    $approved = Get-ItemProperty -LiteralPath $s.Approved -ErrorAction SilentlyContinue
    $run = Get-ItemProperty -LiteralPath $s.Run -ErrorAction SilentlyContinue
    if ($run) { foreach ($p in $run.PSObject.Properties) { if ($p.Name -notlike 'PS*') {
      $flag = if ($approved) { $approved.($p.Name) } else { $null }
      if (-not ($flag -and ($flag[0] -band 1))) { $out += "$($s.Tag):$($p.Name)" } } } }
  }
  $folders = @(
    @{ Dir = [Environment]::GetFolderPath('Startup'); Approved = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder'; Tag = 'folder' },
    @{ Dir = [Environment]::GetFolderPath('CommonStartup'); Approved = 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder'; Tag = 'common-folder' }
  )
  foreach ($f in $folders) {
    $approved = Get-ItemProperty -LiteralPath $f.Approved -ErrorAction SilentlyContinue
    Get-ChildItem -LiteralPath $f.Dir -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne 'desktop.ini' } | ForEach-Object {
      $flag = if ($approved) { $approved.($_.Name) } else { $null }
      if (-not ($flag -and ($flag[0] -band 1))) { $out += "$($f.Tag):$($_.Name)" }
    }
  }
  $out | Sort-Object -Unique
}
$startupNowList = @(Get-EnabledStartup)
$baseFile = Join-Path $logDir 'startup-enabled-baseline.txt'
if (-not (Test-Path $baseFile)) { Set-Content $baseFile $startupNowList }
$baselineList = @(Get-Content $baseFile)
$info.startupEntries = $startupNowList.Count
$newOnes = @($startupNowList | Where-Object { $baselineList -notcontains $_ })
if ($newOnes.Count -gt 0) { $issues.Add("New startup entries: $($newOnes -join ', '). If you did not add them, disable them in Task Manager > Startup apps.") }

# Last Windows update
$hf = Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 1
if ($hf -and $hf.InstalledOn) {
  $age = ((Get-Date) - $hf.InstalledOn).Days
  $info.lastUpdateDaysAgo = $age
  if ($age -gt 45) { $issues.Add("No Windows update installed for $age days.") }
}

# Power plan on a laptop
if (Get-CimInstance Win32_Battery) {
  $plan = (powercfg /getactivescheme) -replace '.*\(|\).*', ''
  $info.powerPlan = $plan
  if ($plan -match 'High performance|Ultimate') { $issues.Add("Power plan is '$plan', which drains the battery. Balanced is recommended.") }
}

$info.issues = $issues.ToArray()
$info | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $logDir 'pc-health.json')
$lines = @("PC health $(Get-Date -Format 'yyyy-MM-dd HH:mm')", "Temp cleaned: $($info.tempFreedMB) MB", "Issues: $($issues.Count)") + ($issues | ForEach-Object { " - $_" })
$lines | Set-Content (Join-Path $logDir 'pc-health.txt')
$lines
if ($Full) {
  "`nDetails"
  foreach ($d in $info.disks) { "  Drive {0}  {1} GB free ({2}%)" -f $d.drive, $d.freeGB, $d.percentFree }
  "  SSD:            $($info.diskHealth)"
  if ($info.defender) { "  Defender:       real-time $($info.defender.realtime), signatures $($info.defender.signatureAgeDays) day(s) old" }
  if ($info.Contains('batteryHealthPercent')) { "  Battery health: $($info.batteryHealthPercent)%" }
  if ($info.Contains('powerPlan')) { "  Power plan:     $($info.powerPlan)" }
  "  Uptime:         $($info.uptimeDays) day(s); last Windows update $($info.lastUpdateDaysAgo) day(s) ago"
  $os2 = Get-CimInstance Win32_OperatingSystem
  "  RAM free:       {0:N1} of {1:N1} GB" -f ($os2.FreePhysicalMemory / 1MB), ($os2.TotalVisibleMemorySize / 1MB)
  "  Startup apps ($($startupNowList.Count) enabled): " + (($startupNowList | ForEach-Object { $_ -replace '^[a-z-]+:', '' }) -join ', ')
}

# ---------- 3. notify only if something needs attention ----------
if ($issues.Count -gt 0 -and -not $Quiet) {
  try {
    [void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
    $tpl = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
    $t = $tpl.GetElementsByTagName('text')
    [void]$t.Item(0).AppendChild($tpl.CreateTextNode("PC needs attention ($($issues.Count))"))
    [void]$t.Item(1).AppendChild($tpl.CreateTextNode(($issues | Select-Object -First 2) -join ' | '))
    $toast = [Windows.UI.Notifications.ToastNotification]::new($tpl)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe').Show($toast)
  } catch { }
}
