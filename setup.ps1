# setup.ps1 - Automated setup and bootstrap script for Windows Workstation Tools (C:\tools)
[CmdletBinding()]
param(
    [string]$InstallDir = "C:\tools",
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "       Windows Workstation Tools Setup & Bootstrap      " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

# 1. Ensure Install Directory Exists
if (-not (Test-Path $InstallDir)) {
    Write-Host "[*] Creating tools directory: $InstallDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

# 2. Add C:\tools to User PATH if missing
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -split ';' -notcontains $InstallDir) {
    Write-Host "[*] Adding $InstallDir to User PATH..." -ForegroundColor Yellow
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$InstallDir", "User")
    $env:Path = "$env:Path;$InstallDir"
    Write-Host "[+] $InstallDir added to PATH! (Active in new shells)" -ForegroundColor Green
} else {
    Write-Host "[+] $InstallDir is already in User PATH." -ForegroundColor Green
}

# 3. Synchronize launchers and verify shell shims
Write-Host "[*] Synchronizing tool launchers..." -ForegroundColor Cyan
$toolsScript = Join-Path $InstallDir "tools.ps1"
if (Test-Path $toolsScript) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $toolsScript sync -Fix
}

# 4. Run Health Audit
Write-Host "[*] Verifying installed tools health..." -ForegroundColor Cyan
if (Test-Path $toolsScript) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $toolsScript doctor
}

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host " Setup complete! Restart your terminal to refresh PATH. " -ForegroundColor Green
Write-Host " Type 'tools' or 'tools find <word>' to explore tools.  " -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Cyan
