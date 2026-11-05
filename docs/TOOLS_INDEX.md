# Master Workstation & AI Agent Tools Index

**Agents: start with `C:\tools\AGENTS.md` and the `tools` command (`tools find <word>`, `tools show <name>`, `tools doctor`). Machine-readable data: `C:\tools\tools.json`.**

Comprehensive inventory of all verified CLI utilities, graph intelligence engines, system analyzers, browser tools, and cloud backup suites installed across `C:\tools` and `%USERPROFILE%\tools`.

---

## 1. Browser Automation & QA Protocol Suite

| Tool Name | Tier | Primary Purpose | Installation Path / Location | Command / Usage |
| :--- | :--- | :--- | :--- | :--- |
| **`agent-browser`** | Tier 1 (Default) | Ultra-low token browser automation, `@ref` snapshots, fast visual diffing | npm global (`%APPDATA%\npm\agent-browser.cmd`, v0.37.1)<br>`%USERPROFILE%\.agent-browser\` | `agent-browser open <url>`<br>`agent-browser snapshot -i`<br>`agent-browser click @ref` |
| **`playwright-cli`** | Tier 2 (Test Suites) | Complex E2E assertion test suites, codegen, multi-browser testing | `C:\tools\playwright-cli.cmd`<br>`%LOCALAPPDATA%\ms-playwright` | `playwright-cli test`<br>`playwright-cli codegen` |
| **`browser_subagent`**| Tier 3 (Visual Rec) | Autonomous visual subagent with automatic WebP video recording | Native Antigravity Subagent | Internal agent tool call |

---

## 2. Everything Search Engine (GUI & CLI Integration)

| Tool Component | Type | Location / Access Path | Description & Usage |
| :--- | :--- | :--- | :--- |
| **`Everything` (GUI)** | Desktop Application | `%USERPROFILE%\tools\Everything\Everything.lnk` | Real-time NTFS desktop search window for instant file lookup across all drives. |
| **`EverythingToolbar`** | Windows Taskbar Integration | `%USERPROFILE%\tools\Everything\EverythingToolbar.lnk` | Embeds the Everything search bar directly into the Windows taskbar. |
| **`es-mini` / `es.exe`** | CLI Search Interface | `C:\tools\es-mini.cmd`<br>`C:\tools\es.exe` | Command-line interface querying the Everything IPC indexer in sub-milliseconds.<br>**Usage:** `es-mini "filename.ext"` |
| **Service Status** | System Service / Process | Background Process | Note: `es-mini` requires the `Everything.exe` service to be running in the background. |

---

## 3. Windows System Analysis & Diagnostics Suite

| Tool Name | Location | Category | Capabilities & Purpose | Command / Syntax |
| :--- | :--- | :--- | :--- | :--- |
| **`autorunsc64.exe`** | `Sysinternals` | Security & Persistence | Analyzes all Windows startup registry keys, services, tasks, & malware persistence points | `autorunsc64.exe -a *` |
| **`sigcheck64.exe`** | `Sysinternals` | Security & VirusTotal | Verifies digital code signatures and queries VirusTotal (70+ AV engines) via file hash | `sigcheck64.exe -nobanner -vt -u <file>` |
| **`czkawka.exe`** | Rust CLI (`czkawka-cli`) | Disk & Deduplication | Ultra-fast duplicate file finder, empty folder detector, and large file analyzer | `czkawka dup -d <dir>` |
| **`clean-temp.cmd`** | Custom Utility | Disk Maintenance | Safely purges stale temporary files without touching locked files | `clean-temp` |
| **`wsl-compact.cmd`** | Custom Utility | Virtual Disk Compactor | Safely compacts WSL2 (`ext4.vhdx`) and Docker virtual disks via diskpart | `wsl-compact [-Docker]` |
| **`btop`** | Terminal Monitor | System Resource TUI | Beautiful terminal monitor for real-time CPU, RAM, disks, and processes | `btop` |
| **`handle64.exe`** | `Sysinternals` | File Lock Analysis | Inspects open file handles, locked DLLs, and process file locks | `handle64.exe <file-path>` |
| **`RAMMap64.exe`** | `Sysinternals` | Memory Diagnostics | Advanced physical RAM analyzer (Paged Pool, Nonpaged Pool, Mapped Files) | `RAMMap64.exe` |
| **`Toolbox` (`toolbox.cmd`)** | `Toolbox` | System Suite | PC health diagnostics (`/status`, `/boost`, `/clean`, `/diagnose`, `/security`, `/unlock`) | `toolbox Status -Compact` |
| **`Optimizer`** | `Optimizer` | OS Tuning | Windows registry tuner, privacy enforcer, and telemetry blocker | `Optimizer-16.7.exe` |
| **`WinUtil`** | `WinUtil` | Package & OS Utility | Chris Titus Tech Windows debloater, tweak engine, and package installer | `Launch-WinUtil.cmd` |
| **`MemReduct`** | `MemReduct` | Memory Cleaner | Real-time RAM memory reduction engine and working set cleaner | `memreduct.exe` |
| **`BleachBit`** | `BleachBit\BleachBit-Portable` | Disk Scrubber | Privacy scrubber, browser cache cleaner, and junk file remover | `bleachbit.exe` (GUI), `bleachbit_console.exe` (CLI) |
| **`Fastfetch`** | `Fastfetch` | Environment Info | Terminal hardware, system OS, and uptime fetcher | `fastfetch` |

---

## 4. Code Intelligence & Low-Token Performance Tools (`C:\tools`)

| Tool / Wrapper | Technology | Primary Domain | Command / Usage |
| :--- | :--- | :--- | :--- |
| **`code-check`** | Orchestrator (Ruff + Oxlint + ast-grep + Pyright + tsc) | Unified multi-language static analysis, auto-fixer, agent JSON IR | `code-check [dir]`<br>`code-check --deep`<br>`code-check --changed`<br>`code-check --fix`<br>`code-check --agent`<br>`code-check --watch` |
| **`ruff.exe`** | Ruff (Rust) | Ultra-fast Python linter & code formatter | `ruff check [file/dir]`<br>`ruff check --fix` |
| **`oxlint`** (npm global, `%APPDATA%\npm`, v1.85.0) | Oxlint (Rust/Oxc) | Ultra-fast JS/TS linter (React hooks, syntax, correctness) | `oxlint [file/dir]` |
| **`pyright`** (npm global, `%APPDATA%\npm`, v1.1.414) | Pyright (Microsoft) | High-performance Python static type checker | `pyright [dir]` |
| **`cbm` / `cbm-mini`** | Codebase Memory (MCP) | AST symbol links, call graphs, architecture overview | `cbm arch`<br>`cbm search <query>`<br>`cbm trace <func>` |
| **`rg-mini` / `rg.exe`** | Ripgrep | Literal text & regex code search (hard-capped at 20 lines) | `rg-mini "<query>" [dir]` |
| **`fd-mini` / `fd.exe`** | Fd-find | Fast filesystem path & pattern finder (hard-capped at 20 results) | `fd-mini "<pat>" [dir]` |
| **`sg-mini` / `sg.exe`** | Ast-grep | Structural code search & AST pattern matching | `sg-mini run -p "<pat>" --lang <lang>` |
| **`tokei.exe`** | Tokei | Lines of code, language breakdown, blanks, comments | `tokei [dir] --output json \| jq '.languages'` |
| **`hyperfine.exe`** | Hyperfine | CLI execution statistical benchmarking (mean, min, max, stddev) | `hyperfine "<cmd1>" "<cmd2>"` |
| **`jq.exe`** | JQ | High-performance JSON processor & token reducer | `... \| jq '<filter>'` |
| **`7z.exe`** | 7-Zip | High-ratio archive compression & extraction | `7z a <arc> <files>`<br>`7z x <arc> -o<dir>` |
| **`uv.exe` / `uvx.exe`** | Astral UV | High-speed Python package manager, venv manager, script runner | `uv run <script.py>`<br>`uv pip install <pkg>` |

---

## 5. Workflow Automation

| Component | Location | Functionality | Command / Usage |
| :--- | :--- | :--- | :--- |
| **`antigravity-auto-submit`** | `%USERPROFILE%\tools` / `C:\tools` | Active background CDP daemon (`auto-accept.js`) auto-approving terminal modals safely | `auto-accept --status`<br>`auto-accept --pause` |
| **`codex`** | `C:\tools\codex.cmd` | OpenAI Codex CLI binary shortcut in PATH | `codex --version`<br>`codex <args>` |

---

## 6. Designer Web & Asset Generation Pipeline

| Tool | Type | Usage |
| :--- | :--- | :--- |
| **`generate_image`** | Native AI Tool | Creates custom 3D icons, UI mockups, hero art, and texture maps. |
| **`pwa-asset-generator`** | `npx` Package | Generates favicons, Apple touch icons, and PWA splash screens from SVGs. |
| **`svgl-cli`** | `npx` Package | Fetches vector brand & tech logos directly into component folders. |
| **`sharp`** | Node.js Library | Programmatic WebP conversion, image resizing, and color palette extraction. |
| **`shadcn@latest`** | `npx` Scaffolder | Injects accessible React/Tailwind UI primitives. |
| **`magicui-cli`** | `npx` Scaffolder | Injects animated UI components & micro-interactions into projects. |
| **`Mermaid CLI` (`mmdc`)** | `C:\tools` | CLI converter rendering markdown diagrams to PNG/SVG (`mmdc -i input.mmd`). |

---

## 7. Antigravity Temp & Scratch Cleanup Suite

| Tool Command | Location | Primary Purpose | Usage |
| :--- | :--- | :--- | :--- |
| **`antigravity-find-temp`** / **`agy-find-temp`** | `C:\tools\antigravity-find-temp.cmd` | Dry-run scanner finding temporary scripts, scratch files, session logs, browser recordings, and `%TEMP%` dumps with disk sizes | `agy-find-temp` |
| **`antigravity-clean`** / **`agy-clean`** | `C:\tools\antigravity-clean.cmd` | Purges selected or all temporary categories (`--scratch`, `--logs`, `--recordings`, `--temp`, `--all`, `-f`) | `agy-clean --scratch`<br>`agy-clean --all -f` |
| **`antigravity-check`** / **`agy-check`** | `C:\tools\antigravity-check.cmd` | Health check and integrity verifier for Antigravity environment | `agy-check` |
| **`antigravity-brain`** / **`agy-brain`** | `C:\tools\antigravity-brain.cmd` | Brain directory analyzer and storage inspector | `agy-brain` |

---

## 8. Cloud Backup & Personal Knowledge Archive (`C:\tools`)

| Tool Command | Location | Primary Purpose | Usage |
| :--- | :--- | :--- | :--- |
| **`tg-backup stats`** | `C:\tools\tg-backup.cmd` | Comprehensive analytics dashboard of Telegram Drive cloud archive (counts, size, timeline, breakdown) | `tg-backup stats [--json]` |
| **`tg-backup ls` / `list`** | `C:\tools\tg-backup.cmd` | Folder-grouped archive file lister with type icons, subtotals, and sorting | `tg-backup ls [--flat] [--group type] [--type pdf]` |
| **`tg-backup search`** | `C:\tools\tg-backup.cmd` | Smart token and fuzzy relevance search across all cloud file metadata | `tg-backup search "operating systems"` |
| **`tg-backup find`** | `C:\tools\tg-backup.cmd` | Composable filter engine (`--type`, `--ext`, `--min-size`, `--max-size`, `--after`, `--before`, `--largest`, `--newest`) | `tg-backup find --largest 5`<br>`tg-backup find --min-size 1GB` |
| **`tg-backup duplicates`** | `C:\tools\tg-backup.cmd` | Duplicate file identifier and reclaimable cloud storage calculator | `tg-backup duplicates` (or `dupes`) |
| **`tg-backup groups`** | `C:\tools\tg-backup.cmd` | Smart detector for multipart archives (`.part1.rar`), course series, and paired PDF+MP4 files | `tg-backup groups` |
| **`tg-backup backup`** | `C:\tools\tg-backup.cmd` | Direct upload to Telegram Drive with file categorization or 7z compressed snapshots | `tg-backup backup <path> [--archive]` |
| **`tg-backup status`** | `C:\tools\tg-backup.cmd` | Live transfer queue inspector (`transfers.db`) | `tg-backup status [--limit N]` |
| **`tg-backup watch`** | `C:\tools\tg-backup.cmd` | Live terminal progress monitor with transfer speed meters | `tg-backup watch` |
| **`tg-backup doctor`** | `C:\tools\tg-backup.cmd` | System & MTProto stack diagnostic verifier | `tg-backup doctor` |
| **`tg-backup app`** | `C:\tools\tg-backup.cmd` | Telegram Drive desktop process controller | `tg-backup app <status|start|stop>` |


---

## 9. Agent-Friendly CLI Additions (standalone exes in `C:\tools`, all on PATH)

Installed 2026-10-28 from each project's official GitHub release (winget is broken on this PC). All are single binaries with plain-text or JSON output, so any AI agent can call them.

| Tool | Version | Purpose | Command / Usage |
| :--- | :--- | :--- | :--- |
| **`yq.exe`** | 4.54.1 | Read and edit YAML, JSON, TOML, XML (like `jq` for config files) | `yq '.jobs \| keys' ci.yml`<br>`yq -o=json file.yml` |
| **`just.exe`** | 1.59.0 | Project task runner; agents run `just --list` to discover commands | `just --list`<br>`just <task>` |
| **`shellcheck.exe`** | 0.11.0 | Shell script linter | `shellcheck -f json script.sh` |
| **`actionlint.exe`** | 1.7.12 | GitHub Actions workflow linter | `actionlint -format '{{json .}}'` |
| **`osv-scanner.exe`** | 2.7.0 | Dependency vulnerability scan against the OSV database | `osv-scanner scan source -r .`<br>`osv-scanner --format json` |
| **`duckdb.exe`** | CLI | SQL over CSV, JSON and Parquet files, no server | `duckdb -c "select * from 'data.csv' limit 5"` |
| **`difft.exe`** | 0.71.0 | Structural, syntax-aware diff | `difft old.js new.js` |
| **`xh.exe`** | 0.26.3 | HTTP client with readable JSON (curl alternative) | `xh get https://api.example.com/x` |

Where each lives: `agent-browser`, `oxlint`, `pyright`, `biome`, `eslint`, `tsc`, `playwright` are npm globals in `%APPDATA%\npm`. Backups of replaced scripts are in `C:\tools\_backup`.

---

## 10. Document, Media and Security Additions (2026-10-28)

| Tool | Version | Location | Purpose | Command / Usage |
| :--- | :--- | :--- | :--- | :--- |
| **`pandoc`** | 3.13 | `C:\tools\pandoc.exe` | Convert between Markdown, HTML, DOCX, PDF (with an engine), EPUB, LaTeX and more | `pandoc in.md -o out.docx` |
| **`ffmpeg` / `ffprobe`** | 9.0.2 (essentials) | `C:\tools\ffmpeg.exe`, `ffprobe.exe` | Convert, trim and inspect audio and video | `ffprobe -v error -show_format -of json f.mp4`<br>`ffmpeg -i in.mov out.mp4` |
| **`magick`** | ImageMagick 7.1.2 (portable) | `C:\tools\magick.cmd` -> `C:\tools\imagemagick\` | Resize, convert and inspect images | `magick in.png -resize 50% out.webp`<br>`magick identify f.png` |
| **`tesseract`** | 5.4.0 (eng, osd) | `C:\tools\tesseract.cmd` -> `C:\tools\tesseract\` | OCR from the command line | `tesseract img.png stdout` |
| **`semgrep`** | 1.182.1 | `uv tool` (`%USERPROFILE%\.local\bin`) | Static security analysis | `semgrep --metrics=off --config <rules> <path>` |
| **`python` / `pip`** | 3.12.0 | `%LOCALAPPDATA%\Programs\Python\Python312` (on PATH, ahead of the Store stub) | Python runtime | `python script.py`<br>`uv run script.py` |

Removed: the `supabase` and `semgrep@0.0.1` npm globals (broken / stub). Kept: `vercel`.
Open a new terminal after PATH changes. These tools use no resources when idle; they take about 750 MB of disk together.

---

## 11. PC Care and Container/IaC Security (2026-10-28)

| Tool | Location | Purpose | Command / Usage |
| :--- | :--- | :--- | :--- |
| **`trivy`** 0.76.1 | `C:\tools\trivy.exe` | Scan container images, filesystems, IaC and dependencies for vulnerabilities, secrets and misconfigurations | `trivy fs --scanners vuln,secret,misconfig .`<br>`trivy image <name>` |
| **`pc-care`** | `C:\tools\pc-care.ps1` / `pc-care.cmd` | Weekly upkeep and health watch: deletes %TEMP% files older than 7 days, prunes uv cache, checks disk space, SSD health, Defender, firewall, battery wear, pending reboot, startup creep, update age, power plan. Writes `C:\tools\_logs\pc-health.txt`/`.json` and notifies only when something needs attention. | `pc-care -Check -Quiet` (health only)<br>`pc-care` (cleanup + health) |

PC state changes made 2026-10-28 (snapshot for undo in `C:\tools\_backup\pc-snapshot-2026-10-28`): power plan High performance -> Balanced; startup disabled (reversible in Task Manager > Startup apps): Opera Browser Assistant, Chrome auto-launch, Send to OneNote.

---

## 12. PC Health Commands (updated 2026-10-28)

| Command | Needs admin | What it does |
| :--- | :--- | :--- |
| **`pc-check`** | No | Instant read-only health report: disk space, SSD health, Defender, battery wear, power plan, uptime, RAM, enabled startup apps. Safe for any agent or person to run. |
| **`pc-care`** | No | Upkeep + health: deletes %TEMP% files older than 7 days, prunes uv cache, verifies npm cache, writes `C:\tools\_logs\pc-health.txt/.json`, notifies only if something needs attention. Flags: `-Check` (no cleanup), `-Quiet`, `-Full`. Scheduled weekly as `PC-Care Weekly` (Sunday 13:00). |
| **`pc-10.ps1`** | Yes (self-elevates) | One-time hardening: weekly task, old temp cleanup, Defender PUA and network protection, SSD trim, Windows Update scan, BitLocker/Secure Boot/TPM report, battery report. `-DryRun` previews. Already run 2026-10-28. |

Health thresholds: disk < 15% free, Defender off or signatures > 3 days old, firewall off, battery health < 70%, pending reboot or uptime >= 14 days, update older than 45 days, High performance power plan on a laptop, any NEW enabled startup entry (baseline in `C:\tools\_logs\startup-enabled-baseline.txt`).
Known state: Secure Boot on, TPM ready, BitLocker/Device encryption OFF (turn on in Settings > Privacy & security > Device encryption after saving the recovery key). Battery 80% of design capacity.

---

## 13. Agent Discovery Layer (2026-10-28)

| Item | Purpose |
| :--- | :--- |
| `AGENTS.md` | Short guide for any AI agent: how to find tools, risk levels, recipes, Windows gotchas |
| `tools.json` | Machine-readable manifest (name, category, purpose, usage, risk, check command) for 46+ tools |
| `tools` (`tools.cmd` / `tools.ps1`) | `tools list`, `find <word>`, `show <name>`, `categories`, `doctor` (verifies every tool), `sync [-Fix]` (drift check), `versions [-Latest]`, `-Json` output |

---

## 14. Sync, Versions and Availability (2026-10-28)

**One source of truth:** `C:\tools\tools.json`. `AGENTS.md`, this index and the Antigravity skill `pc-toolbox` (`~/.gemini/config/skills/pc-toolbox`) all point to it. After adding or removing a tool: edit `tools.json`, then run `tools sync` (must print `In sync.`) and `tools doctor`.

**Available in every shell:** `C:\tools`, `%APPDATA%\npm`, `~\.local\bin` and the Python folders are on the persistent user PATH (new terminals pick them up). Git Bash cannot run `.cmd` files by name, so each `.cmd` tool has an extensionless launcher next to it (`tools sync -Fix` creates missing ones). A tool whose name matches a folder (`btop`, `mermaid`) is run with `cmd //c`.

**Versions (checked 2026-10-28 with `tools versions -Latest`):** current: rg 15.2.0, fd 10.5.0, ast-grep 0.51.0, jq 1.8.2, delta 0.20.1, ruff 0.17.3, gitleaks 8.30.1, yq 4.54.1, just 1.59.0, actionlint 1.7.12, osv-scanner 2.7.0, trivy 0.76.1, difftastic 0.71.0, xh 0.26.3, pandoc 3.13, lazygit 0.66.2, fastfetch 2.70.0, ffmpeg 9.0.2, ImageMagick 7.1.2-34, tesseract 5.4.0, duckdb 2.0.0, semgrep 1.182.1.
**Held back on purpose (major version jump; test before upgrading):** tokei 12.1.2 (latest 15.0.0), hyperfine 1.20.0 (latest 2.0.0). **uv 0.12.9** (latest 0.13.6) could not be replaced because other tools were running it; update with `uv self update` when nothing is using it. A stale older `uv.exe` (0.9.24) also sits in `~\.local\bin`; `C:\tools` wins on PATH.

**Notes:** `sg` is now a shim for `ast-grep` (the `sg.exe` binary prints a deprecation banner on every call, which wastes tokens); `sg-mini` calls `ast-grep` directly. `tesseract` engine moved to `C:\tools\tesseract-bin`. `bleachbit` is a shim for the portable console build. Old binaries replaced on 2026-10-28 are in `C:\tools\_backup\bin-2026-10-28`. Downloads were checked against the published checksum where the project publishes one (lazygit, ruff, trivy); delta, ast-grep and fastfetch publish none.
