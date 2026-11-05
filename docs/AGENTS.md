# Agent guide for C:\tools

You are on Windows 11 (Ryzen 5 5600H laptop, 15 GB RAM). Every tool below is on PATH. Read this first.

## Find the right tool
```
tools find <word>      search by name or purpose      (tools find secret)
tools show <name>      purpose, usage, risk, tips     (tools show gitleaks)
tools list [category]  everything, or one category
tools doctor           verify every tool still works  (run it if a tool "disappears")
```
Add `-Json` for machine-readable output. The data lives in `C:\tools\tools.json`; the long-form index is `C:\tools\TOOLS_INDEX.md`.

## Risk levels (field `risk`)
- `read`: changes nothing. Use freely.
- `write`: creates or edits files, installs packages. Fine inside the user's project; tell the user what you changed.
- `destructive`: deletes files or changes system state (`pc-care` cleanup, `bleachbit --clean`, `agy-clean*`). Preview first (`pc-care -Check`, `bleachbit --preview`, `agy-find-temp`) and ask before running.
- `admin`: needs elevation (`pc-10.ps1`). Do not run unattended; the user approves UAC.

## Recipes
| Question | Do this |
|---|---|
| Is the PC healthy / slow / low on space? | `pc-check` (read-only). Details: `C:\tools\_logs\pc-health.txt` |
| What starts with Windows? | `pc-check` lists enabled startup apps; full list: `autorunsc64.exe -a * -c` |
| Find a file anywhere | `es "name"` (needs Everything, running at sign-in) |
| Find code | `rg -n "text"`, structural: `sg run -p "<pattern>" --lang js`, symbols/architecture: `cbm search` / `cbm arch` |
| Lint a project | `code-check <dir> --agent` |
| Security check of a repo | `gitleaks detect --no-banner --redact`, `osv-scanner scan source -L <lockfile>`, `trivy fs --scanners vuln,secret,misconfig .`, `semgrep --metrics=off --config <rules> .` |
| Scan binary for signatures / VirusTotal | `sigcheck64 -nobanner -vt -u <file.exe>` |
| Find duplicate files / disk bloat | `czkawka dup -d <dir>`, `czkawka big -d <dir>`, `czkawka empty-folders -d <dir>` |
| Clean temp files / reclaim disk | `clean-temp` (safe %TEMP% purge), `wsl-compact` (WSL VHDX shrink) |
| Convert a document / image / video | `pandoc`, `magick`, `ffmpeg` |
| Read text from an image | `tesseract img.png stdout` |
| Query data files | `duckdb -c "select ..."`, `jq`, `yq` |
| 9Router (AI gateway, port 20127) | `9r status`; `9r` starts it; `9r restart` |
| Browse a website | `agent-browser open <url>`, `agent-browser snapshot -i` |

## Gotchas learned the hard way
- **Every `.cmd` tool has an extensionless launcher**, so `magick`, `tesseract`, `pc-check`, `tools`, `9r` ... run by bare name in Git Bash as well as PowerShell and cmd. If one is missing, run `tools sync -Fix`. `btop` and `mermaid` match folder names: use `cmd //c "btop"`.
- **`sg` is a shim for `ast-grep`** (the real `sg.exe` prints a deprecation banner every call). Prefer `ast-grep` in new commands.
- **Bash collapses double backslashes** (`\\b` becomes a backspace character). Write regexes and Windows paths with the file-edit tool, not shell heredocs or `python -`.
- `7z` takes `-o` with no space: `7z x a.zip -oOUT`.
- `semgrep`: set `PYTHONUTF8=1` and always pass `--metrics=off`.
- **winget is broken on this PC.** Install tools by downloading the official GitHub release into `C:\tools` (and check the checksum), or `uv tool install` / `npm i -g`.
- Python is 3.12 (`python`, `pip`, `py`); prefer `uv run script.py` for one-off scripts.
- Never print secrets: use `gitleaks --redact`. API keys for IntelliPointer live in `%APPDATA%\IntelliPointer AI\provider-keys.dpapi` (Windows-encrypted); do not read or copy them.
- Large cleanups: `%TEMP%` is shared with other running tools and sessions. Only delete files older than 7 days (that is what `pc-care` does).

## Keeping this folder healthy
- After adding a tool: add it to `tools.json` (name, category, purpose, usage, risk, check) and a line in `TOOLS_INDEX.md`, then run `tools sync` (must say `In sync.`) and `tools doctor`.
- Check for newer versions: `tools versions -Latest` (held on purpose: tokei, hyperfine, major jumps). Back up the old exe to `C:\tools\_backup` before replacing, verify the published checksum, test the new one.
- Weekly upkeep: the `PC-Care Weekly` task runs `pc-care` (Sunday 13:00).
- Backups of replaced scripts and the PC settings snapshot: `C:\tools\_backup`.
