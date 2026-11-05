# Windows Workstation CLI & AI Agent Tool Suite (`C:\tools`)

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?logo=windows&logoColor=white)](#)
[![Shell](https://img.shields.io/badge/Shell-PowerShell%20%7C%20CMD%20%7C%20Git%20Bash-4EAA25?logo=gnu-bash&logoColor=white)](#)
[![Tools](https://img.shields.io/badge/Verified%20Tools-55%2B%20Active-brightgreen)](#)
[![Security](https://img.shields.io/badge/Security-Sigcheck%20%7C%20VirusTotal%20%7C%20Gitleaks%20%7C%20Trivy-blueviolet)](#)

A production-grade, token-efficient suite of command-line tools, system monitors, security checkers, code intelligence wrappers, and automation utilities for Windows workstations and autonomous AI coding agents.

```
                    ┌────────────────────────────────────────────────────────┐
                    │               C:\tools CLI Orchestrator                │
                    │               (tools find / show / doctor)             │
                    └──────────────────────────┬─────────────────────────────┘
                                               │
         ┌───────────────────┬─────────────────┼──────────────────┬──────────────────┐
         ▼                   ▼                 ▼                  ▼                  ▼
  ┌──────────────┐    ┌──────────────┐  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
  │  PC Health   │    │   Security   │  │ Code Intel   │   │ Data & Media │   │   Terminal   │
  │  & Cleaning  │    │  & Auditing  │  │ & Linting    │   │ Conversion   │   │  AI Gateway  │
  ├──────────────┤    ├──────────────┤  ├──────────────┤   ├──────────────┤   ├──────────────┤
  │ pc-check     │    │ sigcheck64   │  │ code-check   │   │ jq / yq      │   │ 9ai          │
  │ pc-care      │    │ autorunsc64  │  │ rg-mini      │   │ duckdb       │   │ agent-browser│
  │ clean-temp   │    │ gitleaks     │  │ fd-mini      │   │ difft / delta│   │ playwright   │
  │ wsl-compact  │    │ trivy        │  │ cbm (graph)  │   │ pandoc       │   │ skillmap     │
  │ btop         │    │ osv-scanner  │  │ ast-grep     │   │ ffmpeg       │   │ auto-accept  │
  │ fastfetch    │    │ semgrep      │  │ tokei        │   │ magick       │   │ kiro         │
  └──────────────┘    └──────────────┘  └──────────────┘   └──────────────┘   └──────────────┘
```

---

## 🚀 Quick Setup (Windows 10 / 11)

### 1. Clone into `C:\tools`
Open PowerShell as Administrator or standard user and clone directly:
```powershell
git clone https://github.com/WillyEverGreen/tools.git C:\tools
cd C:\tools
```

### 2. Run Bootstrap Setup
```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```
`setup.ps1` will:
- Add `C:\tools` and `C:\tools\bin` to your User `PATH` (if not already present).
- Automatically generate extensionless shims for Git Bash and WSL interoperability (`tools sync -Fix`).
- Verify installed tool health and print the system status (`tools doctor`).

---

## 🛠️ Master Tool Manager (`tools`)

The entire suite is indexed in `tools.json` and managed via the `tools` CLI:

```bash
tools list                  # List all indexed tools and categories
tools find <word>           # Search tools by name or capability (e.g. tools find secret)
tools show <name>           # Display purpose, syntax, risk rating, and tips
tools doctor                # Test every tool and verify runtime health
tools sync [-Fix]           # Audit and create missing Git Bash / Bash launchers
```

---

## 📦 Core Feature Highlights

### 1. PC Health, Monitoring & Deep Disk Maintenance
Designed to keep Windows snappy, memory-efficient, and free of disk bloat:

- **`pc-check`**: Live diagnostics snapshot of SSD wear, Windows Defender status, battery health, power profile, RAM usage, and startup applications.
- **`clean-temp`**: Safe 1-click purger for `%LOCALAPPDATA%\Temp` that reclaims gigabytes of stale files while safely skipping files open by active programs.
- **`wsl-compact`**: Shrinks and compacts WSL2 (`ext4.vhdx`) and Docker Desktop virtual hard disks, reclaiming lost disk space from deleted Linux files.
- **`btop`**: Beautiful interactive TUI monitor for CPU cores, RAM, network, disks, and processes.
- **`czkawka`**: Blazing fast Rust duplicate file detector, empty directory cleaner, and large file visualizer.
- **`fastfetch`**: Instant clean hardware/OS summary.

### 2. Enterprise Security & Binary Auditing
- **`sigcheck64`**: Sysinternals digital signature verifier. Automatically queries **VirusTotal (75+ antivirus engines)** via file hash to audit any suspicious installer or binary.
- **`autorunsc64`**: Sysinternals persistence analyzer. Inspects all Windows startup registry keys, drivers, tasks, and services.
- **`gitleaks`**: High-speed secrets scanner detecting leaked API keys, tokens, or private certificates before git commits.
- **`trivy` & `osv-scanner`**: Scans repositories and dependency lockfiles against global CVE vulnerability databases.
- **`semgrep`**: Fast static analysis for security bugs and rule compliance.

### 3. Code Intelligence & Low-Token Wrappers
Engineered specifically for pair-programming AI agents and developers:
- **`code-check`**: Multi-language static analysis orchestrator uniting Ruff (Python), Oxlint (JS/TS), Pyright (types), ast-grep (AST patterns), and Biome. Supports `--fix`, `--agent` (structured JSON), and `--deep`.
- **`rg-mini` / `fd-mini`**: Ripgrep and Fd wrappers hard-capped at 20 lines to prevent token context bloat in AI chat windows.
- **`cbm`**: Codebase Memory AST call graph and architectural symbol search.
- **`tokei`**: Fast codebase lines-of-code and language breakdown.
- **`hyperfine`**: Benchmark CLI commands with statistical confidence intervals.

### 4. Data, Documents & Media Conversion
- **`jq` & `yq`**: Zero-latency JSON and YAML stream processors.
- **`duckdb`**: In-process SQL query engine for CSV, Parquet, and JSON datasets.
- **`difft` & `delta`**: Syntax-aware structural diffing for Git and local files.
- **`ffmpeg` & `magick`**: CLI image and media transcoders.
- **`pandoc` & `tesseract`**: Universal markdown/docx document generator and OCR engine.

### 5. Terminal AI & Workflow Automation
- **`9ai`**: Remote gateway CLI connecting your local terminal directly to 9Router models via encrypted Cloudflare tunnels.
- **`agent-browser`**: Token-efficient browser automation CLI with `@ref` interactive snapshots.
- **`kiro`**: Multi-model proxy routing and swarm execution for Claude, DeepSeek, and Qwen models.
- **`auto-accept`**: Autonomous permission auto-accepter for agent environments.

---

## 🔒 Safety & Risk Tiers

Every tool in the suite is tagged with an operational risk tier in `tools.json`:

| Risk Tier | Meaning | Examples |
|---|---|---|
| **`read`** | Strictly read-only; changes nothing. Safe for autonomous agent invocation. | `pc-check`, `sigcheck64`, `rg-mini`, `fastfetch`, `gitleaks` |
| **`write`** | Creates or modifies local files inside project scopes. | `code-check --fix`, `czkawka dup`, `pandoc` |
| **`destructive`** | Purges disk caches or terminates processes. Always previews before mutating. | `clean-temp`, `wsl-compact`, `bleachbit` |
| **`admin`** | Requires Windows UAC elevation. Never runs unattended. | `pc-10.ps1` |

---

## 📁 Repository Structure

```
tools/
├── bin/                    # Executable CLI launchers (.cmd & Git Bash shims)
│   ├── pc-check.cmd        # PC hardware & health diagnostic
│   ├── clean-temp.cmd      # Safe temporary file cleaner
│   ├── wsl-compact.cmd     # Virtual disk (WSL2/Docker) compactor
│   ├── cbm-mini.cmd        # Low-token code graph & symbol finder
│   ├── rg-mini.cmd         # Low-token ripgrep wrapper (<20 lines)
│   └── ...                 # 50+ Windows & cross-platform CLI launchers
├── docs/                   # Documentation & specifications
│   ├── TOOLS_INDEX.md      # Full tool catalog, flags & command reference
│   ├── AGENTS.md           # LLM agent workflows, prompt recipes & guidelines
│   ├── code-check-README.md# Code-check multi-linter architecture
│   └── tg-backup-README.md # Telegram Drive backup suite documentation
├── rules/                  # Static analysis AST patterns
│   └── ast-grep/           # Security & antipattern detection rules
├── scripts/                # Core PowerShell automation & maintenance scripts
│   ├── pc-care.ps1         # System maintenance & health engine
│   ├── clean-temp.ps1      # Safe temp purger
│   ├── wsl-compact.ps1     # Diskpart VHDX compactor
│   ├── 9r.ps1              # 9Router management engine
│   └── everything-doctor.ps1 # Everything IPC search index health check
├── src/                    # Python engines & modular packages
│   ├── antigravity/        # Antigravity session & cleaner engine
│   ├── code_check/         # Multi-language linter orchestrator
│   ├── diskmax/            # Disk usage & cleanup visualizer
│   ├── tg_backup/          # Telegram cloud backup engine
│   └── utils/              # Stream processing utilities (line-cap)
├── vendor/                 # Bundled third-party tools & assets
│   ├── btop/               # btop4win themes and configuration
│   ├── imagemagick/        # ImageMagick configuration & color profiles
│   ├── mermaid/            # Mermaid diagram renderer
│   └── tesseract-bin/      # Tesseract OCR language datasets
├── .gitignore              # Safe binary & secret exclusion rules
├── README.md               # Repository documentation & guide
├── setup.ps1               # 1-command bootstrap & PATH configuration
├── tools.cmd               # Quick launcher for tools manager
├── tools.json              # Master tool catalog & health registry
└── tools.ps1               # Master tools CLI engine
```

---

## 📄 License
MIT License. Third-party binaries managed by `setup.ps1` are subject to their respective open-source and vendor licenses.

