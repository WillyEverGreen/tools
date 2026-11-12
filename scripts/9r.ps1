# 9r.ps1 - PowerShell wrapper forwarding all arguments to C:\tools\bin\9r.cmd
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

if (-not $Arguments -or $Arguments.Count -eq 0) {
    & "$PSScriptRoot\..\bin\9r.cmd"
} else {
    & "$PSScriptRoot\..\bin\9r.cmd" @Arguments
}
exit $LASTEXITCODE
