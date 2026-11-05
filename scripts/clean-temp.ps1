# clean-temp.ps1 - Safely purges stale temporary files and logs
[CmdletBinding()]
param(
    [switch]$IncludeWindowsTemp
)

$ErrorActionPreference = 'SilentlyContinue'

Write-Host "=== Temp Disk Purger ===" -ForegroundColor Cyan

$tempPaths = @("$env:LOCALAPPDATA\Temp")
if ($IncludeWindowsTemp -and (Test-Path "C:\Windows\Temp")) {
    $tempPaths += "C:\Windows\Temp"
}

$totalDeletedBytes = 0
$skippedFiles = 0

foreach ($basePath in $tempPaths) {
    if (-not (Test-Path $basePath)) { continue }
    
    Write-Host "[*] Scanning $basePath..." -ForegroundColor Gray
    $items = Get-ChildItem -Path $basePath -Force -ErrorAction SilentlyContinue

    foreach ($item in $items) {
        $size = 0
        try {
            if ($item.PSIsContainer) {
                $subFiles = Get-ChildItem -Path $item.FullName -Recurse -File -Force -ErrorAction SilentlyContinue
                $size = ($subFiles | Measure-Object -Property Length -Sum).Sum
                Remove-Item -Path $item.FullName -Recurse -Force -ErrorAction Stop
                $totalDeletedBytes += $size
            } else {
                $size = $item.Length
                Remove-Item -Path $item.FullName -Force -ErrorAction Stop
                $totalDeletedBytes += $size
            }
        } catch {
            # File is currently locked by a running process - safely skip it
            $skippedFiles++
        }
    }
}

$freedMB = [math]::Round($totalDeletedBytes / 1MB, 1)
$freedGB = [math]::Round($totalDeletedBytes / 1GB, 2)

if ($freedGB -ge 1.0) {
    Write-Host "[+] Successfully freed $freedGB GB ($freedMB MB)!" -ForegroundColor Green
} else {
    Write-Host "[+] Successfully freed $freedMB MB!" -ForegroundColor Green
}

if ($skippedFiles -gt 0) {
    Write-Host "[*] Skipped $skippedFiles file(s) currently open by active apps." -ForegroundColor Gray
}
Write-Host "=== Cleanup Complete ===" -ForegroundColor Cyan

