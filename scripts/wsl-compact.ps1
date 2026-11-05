# wsl-compact.ps1 - Safely compacts WSL2 & Docker VHDX virtual disks
[CmdletBinding()]
param(
    [switch]$All,
    [switch]$Docker
)

$ErrorActionPreference = 'SilentlyContinue'

Write-Host "=== WSL2 Disk Compactor ===" -ForegroundColor Cyan

# 1. Locate VHDX disks
$vhdxList = @()

$wslDirs = Join-Path $env:LOCALAPPDATA 'wsl'
if (Test-Path $wslDirs) {
    Get-ChildItem -Path $wslDirs -Filter "*.vhdx" -Recurse -File | ForEach-Object {
        $vhdxList += [PSCustomObject]@{
            Name = "WSL: " + $_.Directory.Name
            Path = $_.FullName
            BeforeBytes = $_.Length
        }
    }
}

if ($All -or $Docker) {
    $dockerPath = Join-Path $env:LOCALAPPDATA 'Docker\wsl\disk\docker_data.vhdx'
    if (Test-Path $dockerPath) {
        $item = Get-Item $dockerPath
        $vhdxList += [PSCustomObject]@{
            Name = "Docker Data"
            Path = $item.FullName
            BeforeBytes = $item.Length
        }
    }
}

if ($vhdxList.Count -eq 0) {
    Write-Host "[!] No WSL2 virtual disks (.vhdx) found." -ForegroundColor Yellow
    exit 0
}

Write-Host "[*] Found $($vhdxList.Count) virtual disk(s):" -ForegroundColor Gray
foreach ($v in $vhdxList) {
    $gb = [math]::Round($v.BeforeBytes / 1GB, 2)
    Write-Host "    - $($v.Name): $gb GB ($($v.Path))" -ForegroundColor Gray
}

# 2. Shutdown WSL cleanly
Write-Host "[*] Shutting down WSL..." -ForegroundColor Yellow
wsl.exe --shutdown
Start-Sleep -Seconds 2

# 3. Compact each disk via diskpart
$totalFreedBytes = 0

foreach ($v in $vhdxList) {
    Write-Host "[*] Compacting $($v.Name)..." -ForegroundColor Cyan
    $tmpScript = [System.IO.Path]::GetTempFileName()
    $commands = @"
select vdisk file="$($v.Path)"
attach vdisk readonly
compact vdisk
detach vdisk
"@
    Set-Content -Path $tmpScript -Value $commands -Encoding ASCII
    
    $proc = Start-Process -FilePath "diskpart.exe" -ArgumentList "/s `"$tmpScript`"" -NoNewWindow -Wait -PassThru
    Remove-Item $tmpScript -Force

    $afterItem = Get-Item $v.Path
    $freed = $v.BeforeBytes - $afterItem.Length
    if ($freed -gt 0) {
        $totalFreedBytes += $freed
        $freedMB = [math]::Round($freed / 1MB, 1)
        Write-Host "    [+] Freed $freedMB MB! (Now: $([math]::Round($afterItem.Length / 1GB, 2)) GB)" -ForegroundColor Green
    } else {
        Write-Host "    [=] Already fully compacted." -ForegroundColor Gray
    }
}

# Enable sparse VHD if available for automatic ongoing management
try {
    wsl.exe --manage Ubuntu --set-sparse true 2>$null
} catch {}

$totalFreedMB = [math]::Round($totalFreedBytes / 1MB, 1)
Write-Host "=== Complete: Freed $totalFreedMB MB total! ===" -ForegroundColor Green

