# `tg-backup`: Telegram Drive Archive Intelligence & Backup Suite

A fast, terminal-based backup and archive retrieval utility designed for power users and AI agents (Antigravity). It integrates directly with the **Telegram Drive** desktop application data layer (`transfers.db`, `workspace.db`, `config.json`) and workstation tools (`7z`, `uv`, `jq`).

`tg-backup` turns your Telegram cloud storage into an indexed, searchable, and manageable personal knowledge engine.

---

## 🚀 Quick Start

`tg-backup` is installed globally in `C:\tools\`. Run it from **any terminal** (PowerShell, CMD, Bash) or let Antigravity execute it:

```powershell
# 1. Inspect archive analytics (size, file counts, type breakdown, timeline)
tg-backup stats

# 2. Browse files grouped by folder (default view)
tg-backup ls

# 3. Search files with smart token & fuzzy relevance matching
tg-backup search "operating systems"
tg-backup search "react routing"

# 4. Find files using composable filters
tg-backup find --largest 5
tg-backup find --type pdf --limit 10
tg-backup find --min-size 1GB --folder "Saved Messages"
tg-backup find --after 2026-01-01

# 5. Detect duplicate files and wasted cloud space
tg-backup duplicates

# 6. Detect multipart archives (.part1.rar), lecture series, and paired files
tg-backup groups

# 7. Check Telegram Drive health and tools
tg-backup doctor

# 8. Back up a local directory (categorized or compressed)
tg-backup backup "D:\MyProject"
tg-backup backup "D:\MyProject" --archive --format 7z --name "MyProject_2026"

# 9. Follow live upload progress
tg-backup watch
```

---

## 📖 Command Reference

### 1. `tg-backup stats`
Generates a comprehensive analytics dashboard of your Telegram Drive storage:
* **Total files and volume**: overall size and counts
* **Channel/Folder distribution**: counts per channel (DM, Saved Messages, custom channels)
* **Type breakdown**: counts and storage percentages for Documents, Media, Archives, Images, Code, Data, Configs
* **Top largest files**: ranked by size with type indicators
* **Archive timeline**: oldest and newest file timestamps
* **JSON support**: `tg-backup stats --json`

### 2. `tg-backup ls` / `list`
Browses backed up files with intelligent hierarchy:
* **Default view**: Cleanly grouped under folder headers (`📁 DM/`, `📁 Saved Messages/`) with item counts and size subtotals.
* **Classic flat view**: `tg-backup ls --flat` (classic tabular layout with emoji type indicators).
* **Group by category**: `tg-backup ls --group type` (groups into Documents, Media, Archives, etc.).
* **Type filter**: `tg-backup ls --type pdf` or `tg-backup ls --type media`.
* **Folder filter**: `tg-backup ls DM` or `tg-backup ls --folder "Saved Messages"`.
* **Folders only**: `tg-backup ls -d` (shows channel folders with file counts).
* **Sorting**: `tg-backup ls -s size` or `tg-backup ls -s name -r` (default is date modified).
* **Uncapped**: `tg-backup ls -a` (shows all files without pagination limits).

### 3. `tg-backup search <query>`
Smart token-based and substring search across all file metadata:
* **Relevance scoring**: Returns matches with exact percentage match scores (100% exact, 70%+ token match).
* **Filter by folder**: `tg-backup search "algorithms" -f "Saved Messages"`.
* **Filter by type**: `tg-backup search "react" -t media`.
* **JSON export**: `tg-backup search "gate" --json`.

### 4. `tg-backup find [options]`
Composable discovery engine allowing multi-parameter queries:
* `--largest N`: Show top N largest files (e.g. `tg-backup find --largest 5`).
* `--newest N`: Show top N newest files.
* `--type <category|ext>`: Filter by category (`documents`, `media`, `archives`, `code`) or extension (`pdf`, `mp4`, `zip`).
* `--ext <.ext>`: Filter by exact extension (e.g. `--ext .rar`).
* `--min-size <spec>`: Minimum size threshold (e.g. `500MB`, `1.5GB`, `100KB`).
* `--max-size <spec>`: Maximum size threshold (e.g. `50MB`).
* `--after <YYYY-MM-DD>`: Files created on or after date.
* `--before <YYYY-MM-DD>`: Files created on or before date.
* `--folder <name>`: Restrict search to specific folder.

### 5. `tg-backup duplicates` (alias: `dupes`)
Scans file inventory for duplicate uploads:
* Detects files sharing identical filenames and exact byte sizes.
* Computes exact reclaimable cloud storage space.
* Lists copies with channel location and timestamps.
* Identifies potential renamed candidates with identical byte counts.

### 6. `tg-backup groups`
Automatically clusters related files:
* **Multipart Archives**: Identifies split archive sets (`.part1.rar`, `.part2.rar`, `.part3.rar` / `.z01`, `.z02`) and displays cumulative sizes.
* **Course & Lecture Series**: Detects numbered sequences (`1.mp4`...`49.mp4`, `Day-1`...`Day-22`, `20.1`...`20.22`).
* **Paired Files**: Automatically links matching documents and lecture videos (e.g. `49.pdf` + `49.mp4`).

### 7. `tg-backup backup <path> [flags]`
Uploads files directly into the Telegram Drive engine:
* **Categorized Mode (`--organize category`, default)**: Categorizes files into structured tags:
  - 📄 `[documents]`: `.pdf`, `.docx`, `.xlsx`, `.md`, `.txt`, `.csv`
  - 💻 `[code]`: `.py`, `.ts`, `.js`, `.rs`, `.go`, `.html`, `.css`, `.sql`
  - 🖼️ `[images]`: `.png`, `.jpg`, `.webp`, `.svg`
  - 🎥 `[media]`: `.mp4`, `.mkv`, `.mp3`, `.wav`
  - 📦 `[archives]`: `.zip`, `.7z`, `.rar`, `.tar`, `.gz`
  - 💾 `[data]`: `.db`, `.sqlite`, `.parquet`, `.dump`
  - ⚙️ `[configs]`: `.yaml`, `.toml`, `.env*`
* **Compressed Mode (`--archive` / `-a`)**: Creates high-compression `.7z` or `.zip` snapshots using `C:\tools\7z.exe`.
* **Target Folder**: `--folder DM` or `--folder <channel_id>`.
* **Dry Run**: Preview the backup plan with `--dry-run`.
* **Automatic Exclusions**: Ignores build artifacts (`node_modules`, `.git`, `dist`, `__pycache__`, `.venv`, `.next`, `*.tmp`, `*.log`).

### 8. `tg-backup status` & `tg-backup watch`
* `tg-backup status [--limit N] [--json]`: Inspects pending, active, and completed jobs in `transfers.db`.
* `tg-backup watch`: Real-time terminal dashboard with progress bars, upload speeds, and status updates.

### 9. `tg-backup app`
* `tg-backup app status`: Checks whether Telegram Drive process is running.
* `tg-backup app start`: Launches Telegram Drive desktop application.
* `tg-backup app stop`: Safely terminates the background app process.

### 10. `tg-backup doctor`
Verifies:
* Telegram Drive application executable (`app.exe`)
* Database accessibility (`transfers.db`, `workspace.db`)
* Telegram account identity and channel bindings
* Workstation tooling (`7z.exe`, `uv.exe`, `py.exe`)

---

## 🛠️ Global Installation & Architecture

* **Executable Wrapper**: `C:\tools\tg-backup.cmd`
* **Core Logic**: `C:\tools\tg_backup.py`
* **Workspace Database**: `%APPDATA%\com.cameronamer.telegramdrive\workspace\<account_id>\workspace.db`
* **Transfer Queue**: `%APPDATA%\com.cameronamer.telegramdrive\transfers.db`
* **Configuration**: `%APPDATA%\com.cameronamer.telegramdrive\config.json`
