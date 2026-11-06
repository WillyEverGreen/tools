<#
  tools - find and verify the CLIs in C:\tools (built for AI agents and people).

    tools list [category]     all tools, or one category
    tools find <word>         search name, category, purpose
    tools show <name>         purpose, usage, risk and tips for one tool
    tools doctor              run each tool's check command and report which work
    tools categories          list categories
    tools sync [-Fix]         drift check: undocumented tools, missing tools, missing Git Bash launchers,
                              duplicate copies; -Fix creates the missing launchers
    tools versions [-Latest]  installed versions of the main tools (-Latest also asks GitHub what is newest)
  Add -Json to any command for machine-readable output.   Data: C:\tools\tools.json
#>
param([Parameter(Position = 0)][string]$Cmd = 'list', [Parameter(Position = 1)][string]$Arg = '', [switch]$Json, [switch]$Fix, [switch]$Latest)

if ($env:Path -split ';' -notcontains 'C:\tools\bin') {
    $env:Path = "$env:Path;C:\tools\bin"
}

$manifest = Get-Content 'C:\tools\tools.json' -Raw | ConvertFrom-Json
$all = @($manifest.tools)

function Out-Rows($rows) {
  if ($Json) { $rows | ConvertTo-Json -Depth 4 }
  else { $rows | ForEach-Object { '{0,-14} {1,-12} {2,-11} {3}' -f $_.name, $_.category, $_.risk, $_.purpose } }
}

switch ($Cmd.ToLower()) {
  'list' {
    $rows = if ($Arg) { $all | Where-Object { $_.category -eq $Arg } } else { $all }
    if (-not $Json) { '{0,-14} {1,-12} {2,-11} {3}' -f 'NAME', 'CATEGORY', 'RISK', 'PURPOSE' }
    Out-Rows $rows
  }
  'categories' { $all | Group-Object category | Sort-Object Name | ForEach-Object { '{0,-14} {1}' -f $_.Name, (($_.Group | ForEach-Object name) -join ', ') } }
  'find' {
    if (-not $Arg) { 'Usage: tools find <word>'; exit 1 }
    $rows = $all | Where-Object { "$($_.name) $($_.category) $($_.purpose) $($_.usage)" -match [regex]::Escape($Arg) }
    if (-not $rows) { "No tool matches '$Arg'."; exit 1 }
    Out-Rows $rows
  }
  'show' {
    $t = $all | Where-Object { $_.name -eq $Arg }
    if (-not $t) { "Unknown tool '$Arg'. Try: tools find $Arg"; exit 1 }
    if ($Json) { $t | ConvertTo-Json -Depth 4 } else {
      "name:     $($t.name)"; "category: $($t.category)"; "risk:     $($t.risk)"; "purpose:  $($t.purpose)"; "usage:    $($t.usage)"
      if ($t.tip) { "tip:      $($t.tip)" }
    }
  }
  'doctor' {
    $env:PYTHONUTF8 = '1'
    $results = foreach ($t in $all | Where-Object { $_.check }) {
      $first = ($t.check -split ' ')[0]
      $found = [bool](Get-Command $first -ErrorAction SilentlyContinue)
      $ok = $false
      if ($found) {
        # Only commands marked read-only are executed; others are checked for presence.
        if ($t.risk -eq 'read') { $null = & cmd /c "$($t.check) >nul 2>&1"; $ok = ($LASTEXITCODE -eq 0) } else { $ok = $true }
      }
      [pscustomobject]@{ name = $t.name; found = $found; works = $ok }
    }
    if ($Json) { $results | ConvertTo-Json } else {
      $results | ForEach-Object { '{0,-6} {1}' -f $(if ($_.works) { 'ok' } else { 'FAIL' }), $_.name }
      $bad = @($results | Where-Object { -not $_.works }).Count
      "`n$($results.Count - $bad) of $($results.Count) tools OK" + $(if ($bad) { ", $bad need attention" } else { '' })
    }
  }
  'sync' {
    $dir = 'C:\tools'
    $binDir = Join-Path $dir 'bin'
    $files = @(Get-ChildItem $dir -File | Where-Object { $_.Name -notmatch '^(_|tools\.|AGENTS|TOOLS_INDEX|README|setup)' })
    if (Test-Path $binDir) { $files += @(Get-ChildItem $binDir -File) }
    $bare = $files | Where-Object { $_.Extension -in '.exe', '.cmd', '.ps1', '.bat' } | ForEach-Object { [IO.Path]::GetFileNameWithoutExtension($_.Name).ToLower() } | Sort-Object -Unique
    $documented = $all | ForEach-Object { $_.name.ToLower() -replace '\.ps1$', '' }
    # Families documented by one manifest entry (Antigravity helpers, start/stop scripts, internals).
    $family = '^(agy-|antigravity|check-|clean-|claude-|ides-|start-|stop-|status-|update-|kiro|cbm-|diskmax|7zr|btm|code_check|antigravity_|tg_backup|session-manager|line-cap|d2|kondo|lazygit|everything-|md-mermaid|mermaid|9router-|session)'
    $undocumented = @($bare | Where-Object { $documented -notcontains $_ -and $_ -notmatch $family -and $_ -notin 'tools', 'es-mini', 'rg-mini', 'fd-mini', 'sg-mini', 'ffprobe', 'pc-care', 'pc-10', 'tesseract', 'magick', 'ast-grep', 'codebase-memory-mcp', 'autorunsc', 'autorunsc64', 'clean-all', 'ides-check', '7z', 'uvx' })
    $missing = @($all | Where-Object { -not (Get-Command ($_.name -replace '\.ps1$', '') -ErrorAction SilentlyContinue) -and -not (Test-Path (Join-Path $dir $_.name)) -and -not (Test-Path (Join-Path $binDir $_.name)) -and -not (Test-Path (Join-Path $dir "scripts\$($_.name)")) } | ForEach-Object name)
    # Git Bash cannot run .cmd files by name: each needs an extensionless launcher in bin/.
    $cmds = if (Test-Path $binDir) { Get-ChildItem $binDir -Filter *.cmd -File | Where-Object { $_.Name -notmatch '^_' -and -not (Test-Path (Join-Path $binDir ($_.BaseName + '.exe'))) -and -not (Test-Path (Join-Path $dir ($_.BaseName + '.exe'))) } } else { @() }
    $noLauncher = @($cmds | Where-Object { -not (Test-Path -LiteralPath (Join-Path $binDir $_.BaseName)) } | ForEach-Object BaseName)
    if ($Fix) {
      foreach ($n in $noLauncher) {
        $body = "#!/usr/bin/env sh`n# Launcher so Git Bash can run the Windows .cmd tool by name.`nexec cmd //c `"`$(cygpath -w `"`$(dirname `"`$0`")/$n.cmd`")`" `"`$@`"`n"
        [IO.File]::WriteAllText((Join-Path $binDir $n), $body, (New-Object Text.UTF8Encoding($false)))
      }
    }
    $dupes = @()
    # The npm-global Antigravity wrappers are kept in sync with C:\tools on purpose, so they are not reported.
    $npmDir = Join-Path $env:APPDATA 'npm'
    foreach ($n in $bare) {
      $other = @(Get-Command $n -All -ErrorAction SilentlyContinue | Where-Object { $_.Source -and $_.Source -notlike "$dir\*" -and $_.CommandType -eq 'Application' -and -not ($_.Source -like "$npmDir\*" -and $n -match $family) })
      if ($other.Count) { $dupes += "$n -> $($other[0].Source)" }
    }
    $result = [ordered]@{ tools = $all.Count; undocumented = $undocumented; missing = $missing; missingGitBashLaunchers = $(if ($Fix) { @() } else { $noLauncher }); launchersCreated = $(if ($Fix) { $noLauncher } else { @() }); otherCopiesOnPath = $dupes }
    if ($Json) { $result | ConvertTo-Json -Depth 3 } else {
      "Manifest entries:            $($all.Count)"
      "Undocumented tools:          $($undocumented.Count) $(if ($undocumented.Count) { '-> ' + ($undocumented -join ', ') })"
      "Manifest tools not found:    $($missing.Count) $(if ($missing.Count) { '-> ' + ($missing -join ', ') })"
      "Missing Git Bash launchers:  $($result.missingGitBashLaunchers.Count) $(if ($result.missingGitBashLaunchers.Count) { '-> ' + ($result.missingGitBashLaunchers -join ', ') + '   (run: tools sync -Fix)' })"
      if ($Fix) { "Launchers created:          $($noLauncher.Count)" }
      "Other copies earlier/later on PATH: $($dupes.Count) $(if ($dupes.Count) { '-> ' + (($dupes | Select-Object -First 5) -join '; ') })"
      if (-not ($undocumented.Count -or $missing.Count -or $result.missingGitBashLaunchers.Count)) { 'In sync.' } else { 'Add undocumented tools to C:\tools\tools.json, then re-run.' }
    }
  }
  'versions' {
    $env:PYTHONUTF8 = '1'
    $probe = [ordered]@{
      rg = @('rg --version', 'BurntSushi/ripgrep'); fd = @('fd --version', 'sharkdp/fd'); sg = @('sg --version', 'ast-grep/ast-grep'); jq = @('jq --version', 'jqlang/jq')
      tokei = @('tokei --version', 'XAMPPRocky/tokei'); hyperfine = @('hyperfine --version', 'sharkdp/hyperfine'); delta = @('delta --version', 'dandavison/delta')
      ruff = @('ruff --version', 'astral-sh/ruff'); uv = @('uv --version', 'astral-sh/uv'); gitleaks = @('gitleaks version', 'gitleaks/gitleaks'); yq = @('yq --version', 'mikefarah/yq')
      just = @('just --version', 'casey/just'); actionlint = @('actionlint -version', 'rhysd/actionlint'); 'osv-scanner' = @('osv-scanner --version', 'google/osv-scanner')
      trivy = @('trivy --version', 'aquasecurity/trivy'); difft = @('difft --version', 'Wilfred/difftastic'); xh = @('xh --version', 'ducaale/xh'); pandoc = @('pandoc --version', 'jgm/pandoc')
      duckdb = @('duckdb --version', 'duckdb/duckdb'); lazygit = @('lazygit --version', 'jesseduffield/lazygit'); fastfetch = @('fastfetch --version', 'fastfetch-cli/fastfetch')
    }
    $rows = foreach ($k in $probe.Keys) {
      $raw = (& cmd /c "$($probe[$k][0]) 2>&1" | Select-Object -First 1) -as [string]
      $inst = [regex]::Match($raw, '\d+\.\d+(\.\d+)?').Value
      $new = ''
      if ($Latest -and (Get-Command gh -ErrorAction SilentlyContinue)) { $t = & gh release view -R $probe[$k][1] --json tagName -q .tagName 2>$null; $new = [regex]::Match([string]$t, '\d+\.\d+(\.\d+)?').Value }
      [pscustomobject]@{ tool = $k; installed = $inst; latest = $new; outdated = [bool]($new -and $inst -and ([version]($new + $(if ($new -notmatch '\d+\.\d+\.\d+') { '.0' })) -gt [version]($inst + $(if ($inst -notmatch '\d+\.\d+\.\d+') { '.0' })))) }
    }
    if ($Json) { $rows | ConvertTo-Json } else { $rows | ForEach-Object { '{0,-12} {1,-10} {2,-10} {3}' -f $_.tool, $_.installed, $_.latest, $(if ($_.outdated) { 'UPDATE' } else { '' }) } }
  }
  default { Get-Help $PSCommandPath | Out-String }
}
