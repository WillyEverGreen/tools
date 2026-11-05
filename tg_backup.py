#!/usr/bin/env python3
"""
tg-backup v2: Telegram Archive Intelligence CLI
Integrates directly with Telegram Drive desktop app (transfers.db, workspace.db, config.json)
and workstation tools (7z, uv, etc.) to provide organized backup, search, analytics, and
duplicate/group detection for your Telegram cloud archive.
"""

import sys
import os
import re
import json
import time
import uuid
import random
import string
import shutil
import sqlite3
import hashlib
import argparse
import subprocess
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any

# --- Constants & Paths ---
APPDATA_ROAMING = os.environ.get("APPDATA", "")
APPDATA_LOCAL = os.environ.get("LOCALAPPDATA", "")

TG_DRIVE_DATA = Path(APPDATA_ROAMING) / "com.cameronamer.telegramdrive"
TG_DRIVE_EXE = Path(APPDATA_LOCAL) / "Telegram Drive" / "app.exe"

CONFIG_FILE = TG_DRIVE_DATA / "config.json"
TRANSFERS_DB = TG_DRIVE_DATA / "transfers.db"
SETTINGS_FILE = TG_DRIVE_DATA / "settings.json"
WORKSPACE_DIR = TG_DRIVE_DATA / "workspace"

TOOLS_DIR = Path(r"C:\tools")
SEVEN_ZIP = TOOLS_DIR / "7z.exe"
if not SEVEN_ZIP.exists():
    which_7z = shutil.which("7z")
    if which_7z:
        SEVEN_ZIP = Path(which_7z)

# Default ignore patterns for backups
DEFAULT_EXCLUDES = [
    "node_modules", ".git", ".github", ".vscode", ".idea",
    "__pycache__", "*.pyc", ".venv", "venv", "env",
    "dist", "build", ".next", ".turbo", "out",
    "*.log", "*.tmp", "*.temp", ".DS_Store", "Thumbs.db",
    "target", ".gemini", ".system_generated"
]

# Category definitions
CATEGORIES = {
    "documents": [".pdf", ".docx", ".doc", ".txt", ".md", ".xlsx", ".xls", ".pptx", ".ppt", ".csv", ".rtf", ".epub", ".mobi"],
    "code": [".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss", ".json", ".rs", ".go", ".java", ".c", ".cpp", ".h", ".cs", ".php", ".sh", ".cmd", ".bat", ".ps1", ".sql"],
    "images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".ico", ".tiff", ".raw"],
    "media": [".mp4", ".mkv", ".mov", ".avi", ".webm", ".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac"],
    "archives": [".zip", ".7z", ".tar", ".gz", ".bz2", ".xz", ".rar", ".iso"],
    "data": [".db", ".sqlite", ".sqlite3", ".bak", ".dump", ".arrow", ".parquet"],
    "configs": [".env", ".env.local", ".env.example", ".yaml", ".yml", ".toml", ".ini", ".conf", ".xml"]
}

# Configure UTF-8 stdout if supported, or replace errors
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# --- ANSI Formatting ---
USE_COLOR = sys.stdout.isatty() or os.environ.get("FORCE_COLOR") == "1"

def c(text: str, color_code: str) -> str:
    if not USE_COLOR:
        return text
    return f"\033[{color_code}m{text}\033[0m"

def bold(text: str) -> str: return c(text, "1")
def green(text: str) -> str: return c(text, "32")
def yellow(text: str) -> str: return c(text, "33")
def cyan(text: str) -> str: return c(text, "36")
def red(text: str) -> str: return c(text, "31")
def gray(text: str) -> str: return c(text, "90")
def blue(text: str) -> str: return c(text, "34")
def magenta(text: str) -> str: return c(text, "35")

def colorize_filename(name: str) -> str:
    """Colorize filename according to file type like GNU ls."""
    ext = Path(name).suffix.lower()
    if ext in CATEGORIES["documents"]:
        return yellow(name)
    elif ext in CATEGORIES["code"]:
        return green(name)
    elif ext in CATEGORIES["media"] or ext in CATEGORIES["images"]:
        return magenta(name)
    elif ext in CATEGORIES["archives"]:
        return red(name)
    elif ext in CATEGORIES["data"]:
        return cyan(name)
    elif ext in CATEGORIES["configs"]:
        return blue(name)
    return name

SYM_OK = "[OK]"
SYM_WARN = "[!]"
SYM_ERR = "[X]"
SYM_INFO = "[*]"

# Type icons for smart categorization
TYPE_ICONS = {
    "documents": "📄",
    "code": "💻",
    "media": "🎥",
    "images": "🖼️",
    "archives": "📦",
    "data": "💾",
    "configs": "⚙️",
    "other": "📁",
}

def get_type_icon(name: str) -> str:
    """Return emoji icon based on file extension category."""
    ext = Path(name).suffix.lower()
    for cat, extensions in CATEGORIES.items():
        if ext in extensions:
            return TYPE_ICONS.get(cat, "📁")
    return "📁"

def parse_size_spec(spec: str) -> int:
    """Parse human-readable size string like '500MB', '1.5GB', '100KB' to bytes."""
    spec = spec.strip().upper()
    multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    for suffix, mult in sorted(multipliers.items(), key=lambda x: -len(x[0])):
        if spec.endswith(suffix):
            try:
                return int(float(spec[:-len(suffix)].strip()) * mult)
            except ValueError:
                break
    # Fallback: try parsing as raw bytes
    try:
        return int(spec)
    except ValueError:
        raise ValueError(f"Cannot parse size: '{spec}'. Use format like '500MB', '1GB', '100KB'.")

def parse_all_items(conn: sqlite3.Connection, where_clauses: list = None, params: list = None) -> List[Dict[str, Any]]:
    """Shared helper to query workspace_files and parse metadata into item dicts."""
    sql = "SELECT key, folder, folder_name, metadata FROM workspace_files"
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
    rows = conn.execute(sql, params or []).fetchall()
    items = []
    for r in rows:
        try:
            meta = json.loads(r[3])
        except (json.JSONDecodeError, TypeError):
            continue
        ext = Path(meta.get("name", "")).suffix.lower()
        cat = "other"
        for category, extensions in CATEGORIES.items():
            if ext in extensions:
                cat = category
                break
        items.append({
            "key": r[0],
            "folder_id": r[1],
            "folder_name": r[2],
            "id": meta.get("id"),
            "name": meta.get("name", "Unknown"),
            "size": meta.get("size", 0),
            "mime_type": meta.get("mime_type", ""),
            "file_ext": ext,
            "category": cat,
            "created_at": meta.get("created_at", ""),
            "encryption_state": meta.get("encryption_state", "plain")
        })
    return items

def fuzzy_match(query: str, name: str) -> float:
    """Score how well a query matches a filename. Returns 0.0-1.0.
    Uses case-insensitive substring + token overlap matching."""
    query_lower = query.lower()
    name_lower = name.lower()

    # Exact substring match = highest score
    if query_lower in name_lower:
        return 1.0

    # Token-based matching: split on non-alphanumeric
    query_tokens = set(re.split(r'[^a-z0-9]+', query_lower))
    query_tokens.discard('')
    name_tokens = set(re.split(r'[^a-z0-9]+', name_lower))
    name_tokens.discard('')

    if not query_tokens:
        return 0.0

    # Count how many query tokens appear in the name (exact or partial)
    matched = 0
    for qt in query_tokens:
        if qt in name_lower:  # partial token match in full name
            matched += 1
        elif any(qt in nt for nt in name_tokens):  # token substring
            matched += 0.7

    score = matched / len(query_tokens)
    return min(score, 1.0)

# --- Helper Functions ---

def generate_job_id() -> str:
    """Generate 9-character alphanumeric ID matching Telegram Drive format."""
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=9))

def format_size(size_bytes: int) -> str:
    """Format bytes into human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def get_file_category(file_path: Path) -> str:
    """Detect file category based on extension."""
    ext = file_path.suffix.lower()
    for category, extensions in CATEGORIES.items():
        if ext in extensions:
            return category
    return "other"

def get_desktop_account_info() -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """Retrieve owner ID and configured folders from Telegram Drive."""
    owner_id = None
    folders = []
    
    # 1. From workspace directory
    if WORKSPACE_DIR.exists():
        subdirs = [d.name for d in WORKSPACE_DIR.iterdir() if d.is_dir() and d.name.isdigit()]
        if subdirs:
            owner_id = subdirs[0]

    # 2. From config.json
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                folders = data.get("folders", [])
        except Exception:
            pass

    # 3. From transfers.db fallback
    if not owner_id and TRANSFERS_DB.exists():
        try:
            conn = sqlite3.connect(str(TRANSFERS_DB))
            row = conn.execute("SELECT payload_json FROM transfer_jobs LIMIT 1").fetchone()
            if row:
                payload = json.loads(row[0])
                owner_id = payload.get("ownerId")
            conn.close()
        except Exception:
            pass

    return owner_id, folders

def is_app_running() -> bool:
    """Check if Telegram Drive process is currently running."""
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", "Get-Process -Name 'app' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Path"],
            stderr=subprocess.DEVNULL,
            text=True
        )
        for line in out.splitlines():
            if "Telegram Drive" in line or "com.cameronamer" in line:
                return True
        return False
    except Exception:
        return False

def start_desktop_app(wait_sec: float = 2.0) -> bool:
    """Launch Telegram Drive app if not running."""
    if is_app_running():
        return True
    if not TG_DRIVE_EXE.exists():
        return False
    try:
        subprocess.Popen([str(TG_DRIVE_EXE)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(wait_sec)
        return is_app_running()
    except Exception:
        return False

# --- Core Database Operations ---

def get_queue_max_position() -> int:
    """Find maximum queue position in transfers.db."""
    if not TRANSFERS_DB.exists():
        return 0
    try:
        conn = sqlite3.connect(str(TRANSFERS_DB))
        cursor = conn.execute("SELECT MAX(queue_position) FROM transfer_jobs")
        row = cursor.fetchone()
        conn.close()
        return row[0] if (row and row[0] is not None) else 0
    except Exception:
        return 0

def enqueue_upload_job(
    file_path: Path,
    owner_id: str,
    folder_id: Optional[int] = None,
    custom_filename: Optional[str] = None
) -> Tuple[bool, str]:
    """Insert upload job directly into Telegram Drive's transfers.db queue."""
    if not TRANSFERS_DB.exists():
        return False, "transfers.db not found. Has Telegram Drive been initialized?"

    if not file_path.exists():
        return False, f"File does not exist: {file_path}"

    job_id = generate_job_id()
    abs_path = str(file_path.resolve())
    filename = custom_filename or file_path.name
    total_bytes = file_path.stat().st_size
    now_ms = int(time.time() * 1000)
    queue_pos = get_queue_max_position() + 1

    payload = {
        "id": job_id,
        "ownerId": str(owner_id),
        "direction": "upload",
        "kind": "local_upload",
        "status": "pending",
        "downloadOutcome": None,
        "path": abs_path,
        "url": None,
        "folderId": folder_id,
        "messageId": None,
        "filename": filename,
        "savePath": None,
        "collisionPolicy": "keep_both",
        "protectionMode": "standard",
        "protectMetadata": True,
        "videoUploadMode": "file",
        "tempZipPath": None,
        "progress": 0,
        "transferredBytes": 0,
        "totalBytes": total_bytes,
        "speedBytesPerSec": 0,
        "error": None,
        "errorCategory": None,
        "persistencePending": False,
        "retryAt": None,
        "queuePosition": queue_pos,
        "revision": 1,
        "createdAt": now_ms,
        "updatedAt": now_ms
    }

    payload_str = json.dumps(payload)

    try:
        conn = sqlite3.connect(str(TRANSFERS_DB))
        conn.execute(
            """
            INSERT INTO transfer_jobs (id, direction, status, queue_position, revision, payload_json, created_at, updated_at)
            VALUES (?, 'upload', 'pending', ?, 1, ?, ?, ?)
            """,
            (job_id, queue_pos, payload_str, now_ms, now_ms)
        )
        conn.commit()
        conn.close()
        return True, job_id
    except Exception as e:
        return False, str(e)

# --- File Collection & Filtering ---

def collect_files(
    target_path: Path,
    recursive: bool = True,
    exclude_patterns: Optional[List[str]] = None
) -> List[Path]:
    """Collect all files matching criteria, respecting exclusions."""
    if exclude_patterns is None:
        exclude_patterns = DEFAULT_EXCLUDES

    if target_path.is_file():
        return [target_path]

    results = []
    
    def matches_exclude(path_obj: Path) -> bool:
        try:
            rel = path_obj.relative_to(target_path)
            parts = rel.parts
        except Exception:
            parts = [path_obj.name]
        
        name = path_obj.name
        for pattern in exclude_patterns:
            if pattern.startswith("*"):
                if name.endswith(pattern[1:]):
                    return True
            elif pattern in parts or pattern == name:
                return True
        return False

    if recursive:
        for root, dirs, files in os.walk(target_path):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if not matches_exclude(Path(root) / d)]
            for file in files:
                fp = Path(root) / file
                if not matches_exclude(fp) and fp.is_file():
                    results.append(fp)
    else:
        for item in target_path.iterdir():
            if item.is_file() and not matches_exclude(item):
                results.append(item)

    return sorted(results)

# --- Commands ---

def cmd_doctor(args: argparse.Namespace) -> None:
    """Run comprehensive diagnostics on Telegram Drive and workstation backup stack."""
    print(bold("\n=== Telegram Drive Workstation Stack Diagnostic ==="))

    # 1. Desktop App Exe
    if TG_DRIVE_EXE.exists():
        print(f"  {green(SYM_OK)} Telegram Drive Executable: {TG_DRIVE_EXE}")
    else:
        print(f"  {red(SYM_ERR)} Telegram Drive Executable not found at expected path: {TG_DRIVE_EXE}")

    # 2. Process Status
    running = is_app_running()
    if running:
        print(f"  {green(SYM_OK)} Desktop App Process: {bold('RUNNING')}")
    else:
        print(f"  {yellow(SYM_WARN)} Desktop App Process: {gray('NOT RUNNING')} (can be auto-started or launched with 'tg-backup app start')")

    # 3. AppData Storage
    if TG_DRIVE_DATA.exists():
        print(f"  {green(SYM_OK)} AppData Directory: {TG_DRIVE_DATA}")
    else:
        print(f"  {red(SYM_ERR)} AppData Directory missing: {TG_DRIVE_DATA}")

    # 4. transfers.db
    if TRANSFERS_DB.exists():
        try:
            conn = sqlite3.connect(str(TRANSFERS_DB))
            count = conn.execute("SELECT COUNT(*) FROM transfer_jobs").fetchone()[0]
            pending = conn.execute("SELECT COUNT(*) FROM transfer_jobs WHERE status='pending'").fetchone()[0]
            active = conn.execute("SELECT COUNT(*) FROM transfer_jobs WHERE status='active'").fetchone()[0]
            conn.close()
            print(f"  {green(SYM_OK)} Transfer Database: {TRANSFERS_DB} (Total jobs: {count}, Pending: {pending}, Active: {active})")
        except Exception as e:
            print(f"  {red(SYM_ERR)} Transfer Database Error: {e}")
    else:
        print(f"  {red(SYM_ERR)} transfers.db missing")

    # 5. Account & Folders
    owner_id, folders = get_desktop_account_info()
    if owner_id:
        print(f"  {green(SYM_OK)} Telegram Account ID: {cyan(owner_id)}")
    else:
        print(f"  {yellow(SYM_WARN)} Telegram Account ID not resolved (login in Telegram Drive first)")

    if folders:
        print(f"  {green(SYM_OK)} Configured Folders / Channels: {len(folders)}")
        for f in folders:
            print(f"      - [{f.get('id')}] {bold(f.get('name', 'Unnamed'))} (Order: {f.get('display_order')})")
    else:
        print(f"  {yellow(SYM_WARN)} No custom channel folders configured (will use default Saved Messages / DM)")

    # 6. Workstation Tools (7z, uv)
    if SEVEN_ZIP.exists():
        print(f"  {green(SYM_OK)} 7-Zip Tool: {SEVEN_ZIP}")
    else:
        print(f"  {yellow(SYM_WARN)} 7z.exe not found in C:\\tools. Archive mode will use zipfile.")

    uv_path = shutil.which("uv")
    if uv_path:
        print(f"  {green(SYM_OK)} Fast Python Runner (uv): {uv_path}")
    else:
        print(f"  {gray('-')} uv runner: not in PATH (using system py launcher)")

    print(bold("\nDiagnosis complete.\n"))

def cmd_app(args: argparse.Namespace) -> None:
    """Manage Telegram Drive desktop application process."""
    action = args.action
    if action == "status":
        if is_app_running():
            print(f"Telegram Drive is {green('RUNNING')}.")
        else:
            print(f"Telegram Drive is {yellow('STOPPED')}.")
    elif action == "start":
        if is_app_running():
            print(f"Telegram Drive is already {green('RUNNING')}.")
        else:
            print("Starting Telegram Drive desktop application...")
            success = start_desktop_app()
            if success:
                print(f"{green('Started successfully.')}")
            else:
                print(f"{red('Failed to start application.')}")
    elif action == "stop":
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", "Stop-Process -Name 'app' -Force -ErrorAction SilentlyContinue"])
            print("Telegram Drive process stopped.")
        except Exception as e:
            print(f"Error stopping process: {e}")

def cmd_status(args: argparse.Namespace) -> None:
    """Inspect the live transfer queue in transfers.db."""
    if not TRANSFERS_DB.exists():
        print(red("Error: transfers.db does not exist."))
        return

    try:
        conn = sqlite3.connect(str(TRANSFERS_DB))
        query = "SELECT id, direction, status, queue_position, payload_json, updated_at FROM transfer_jobs ORDER BY queue_position ASC, updated_at DESC"
        if args.limit:
            query += f" LIMIT {args.limit}"
        rows = conn.execute(query).fetchall()
        conn.close()

        if not rows:
            print("No transfer jobs in queue.")
            return

        if args.json:
            out = []
            for r in rows:
                p = json.loads(r[4])
                out.append({
                    "id": r[0],
                    "direction": r[1],
                    "status": r[2],
                    "position": r[3],
                    "filename": p.get("filename"),
                    "total_bytes": p.get("totalBytes"),
                    "transferred_bytes": p.get("transferredBytes"),
                    "progress": p.get("progress"),
                    "path": p.get("path"),
                    "error": p.get("error")
                })
            print(json.dumps(out, indent=2))
            return

        print(bold(f"\n{'POS':<5} {'ID':<10} {'STATUS':<12} {'PROGRESS':<10} {'SIZE':<10} {'FILENAME'}"))
        print("-" * 75)
        for r in rows:
            job_id, direction, status, pos, payload_raw, updated = r
            try:
                p = json.loads(payload_raw)
                fname = p.get("filename", "Unknown")
                total = p.get("totalBytes", 0)
                prog = p.get("progress", 0)
                status_colored = green(status) if status == "completed" else yellow(status) if status in ("pending", "active") else red(status)
                print(f"{pos:<5} {job_id:<10} {status_colored:<21} {f'{prog}%':<10} {format_size(total):<10} {fname[:35]}")
            except Exception:
                print(f"{pos:<5} {job_id:<10} {status:<12} error parsing payload")
        print()
    except Exception as e:
        print(red(f"Database error: {e}"))

def cmd_stats(args: argparse.Namespace) -> None:
    """Show rich analytics dashboard for Telegram Drive archive."""
    owner_id, folders = get_desktop_account_info()
    if not owner_id:
        print(red("No active account found in workspace."))
        return

    workspace_db = WORKSPACE_DIR / owner_id / "workspace.db"
    if not workspace_db.exists():
        print(red(f"workspace.db not found at {workspace_db}"))
        return

    try:
        conn = sqlite3.connect(str(workspace_db))
        items = parse_all_items(conn)
        folder_stats = conn.execute(
            "SELECT folder_name, COUNT(*) FROM workspace_files GROUP BY folder_name"
        ).fetchall()
        conn.close()

        if not items:
            print(yellow("No files indexed in Telegram Drive workspace."))
            return

        total_files = len(items)
        total_size = sum(x["size"] for x in items)

        # Categorization stats
        cat_counts = defaultdict(int)
        cat_sizes = defaultdict(int)
        for it in items:
            cat_counts[it["category"]] += 1
            cat_sizes[it["category"]] += it["size"]

        top_n = getattr(args, "top", 5) or 5
        largest_files = sorted(items, key=lambda x: x["size"], reverse=True)[:top_n]

        # Dates
        dates = [it["created_at"] for it in items if it["created_at"]]
        oldest = min(dates) if dates else "N/A"
        newest = max(dates) if dates else "N/A"

        # Encryption breakdown
        enc_counts = defaultdict(int)
        for it in items:
            enc_counts[it["encryption_state"]] += 1

        if getattr(args, "json", False):
            payload = {
                "total_files": total_files,
                "total_size": total_size,
                "total_size_human": format_size(total_size),
                "folders": [{"name": f[0], "count": f[1]} for f in folder_stats],
                "categories": {
                    cat: {"count": cat_counts[cat], "size": cat_sizes[cat], "size_human": format_size(cat_sizes[cat])}
                    for cat in cat_counts
                },
                "encryption": dict(enc_counts),
                "oldest": oldest,
                "newest": newest,
                "largest": [{"name": it["name"], "size": it["size"], "size_human": format_size(it["size"]), "folder": it["folder_name"]} for it in largest_files]
            }
            print(json.dumps(payload, indent=2))
            return

        print(bold("\n════ Telegram Drive Archive Statistics ════"))
        print(f"  Total files : {cyan(str(total_files))}")
        print(f"  Total size  : {green(format_size(total_size))}")
        folder_summary = ", ".join([f"{cyan(fname)} ({cnt})" for fname, cnt in folder_stats])
        print(f"  Folders     : {folder_summary}")

        print(bold("\n── Breakdown by Type ──────────────────────────────"))
        ordered_cats = ["documents", "media", "archives", "code", "images", "data", "configs", "other"]
        for cat in ordered_cats:
            cnt = cat_counts.get(cat, 0)
            if cnt > 0:
                sz = cat_sizes.get(cat, 0)
                icon = TYPE_ICONS.get(cat, "📁")
                pct = (sz / total_size * 100) if total_size > 0 else 0
                print(f"  {icon} {cat.capitalize():<12} {cnt:>4} files   {format_size(sz):>9}  {gray(f'({pct:>4.1f}%)')}")

        print(bold("\n── Top Largest Files ──────────────────────────────"))
        for idx, it in enumerate(largest_files, 1):
            icon = get_type_icon(it["name"])
            fn = it["folder_name"]
            print(f"  {idx}. {bold(format_size(it['size'])):>9}  {icon} {colorize_filename(it['name'])}  {gray(f'({fn})')}")

        print(bold("\n── Archive Timeline ───────────────────────────────"))
        print(f"  Oldest file : {gray(oldest[:16])}")
        print(f"  Newest file : {gray(newest[:16])}")

        plain_cnt = enc_counts.get("plain", 0)
        enc_cnt = total_files - plain_cnt
        print(f"  Security    : {gray(str(plain_cnt))} standard, {green(str(enc_cnt))} encrypted (enc2)")
        print()

    except Exception as e:
        print(red(f"Error computing stats: {e}"))

def cmd_find(args: argparse.Namespace) -> None:
    """Discover files using composable filters."""
    owner_id, folders = get_desktop_account_info()
    if not owner_id:
        print(red("No active account found in workspace."))
        return

    workspace_db = WORKSPACE_DIR / owner_id / "workspace.db"
    if not workspace_db.exists():
        print(red(f"workspace.db not found at {workspace_db}"))
        return

    try:
        conn = sqlite3.connect(str(workspace_db))
        items = parse_all_items(conn)
        conn.close()

        filtered = items

        # Folder filter
        folder_filter = getattr(args, "folder", None)
        if folder_filter:
            filtered = [x for x in filtered if x["folder_name"].lower() == folder_filter.lower()]

        # Type filter (category or extension)
        type_filter = getattr(args, "type", None)
        if type_filter:
            tf = type_filter.lower().lstrip(".")
            if tf in CATEGORIES:
                filtered = [x for x in filtered if x["category"] == tf]
            else:
                filtered = [x for x in filtered if x["file_ext"].lstrip(".") == tf]

        # Ext filter
        ext_filter = getattr(args, "ext", None)
        if ext_filter:
            ef = ext_filter.lower()
            if not ef.startswith("."):
                ef = "." + ef
            filtered = [x for x in filtered if x["file_ext"] == ef]

        # Min size
        min_size_str = getattr(args, "min_size", None)
        if min_size_str:
            min_b = parse_size_spec(min_size_str)
            filtered = [x for x in filtered if x["size"] >= min_b]

        # Max size
        max_size_str = getattr(args, "max_size", None)
        if max_size_str:
            max_b = parse_size_spec(max_size_str)
            filtered = [x for x in filtered if x["size"] <= max_b]

        # Date after / before
        after_date = getattr(args, "after", None)
        if after_date:
            filtered = [x for x in filtered if x["created_at"] and x["created_at"] >= after_date]

        before_date = getattr(args, "before", None)
        if before_date:
            filtered = [x for x in filtered if x["created_at"] and x["created_at"] <= before_date]

        # Query / substring pattern if provided
        query = getattr(args, "query", None)
        if query:
            q_lower = query.lower()
            filtered = [x for x in filtered if q_lower in x["name"].lower()]

        # Sorting & Limit
        limit = None
        if getattr(args, "largest", None):
            filtered.sort(key=lambda x: x["size"], reverse=True)
            limit = args.largest
        elif getattr(args, "newest", None):
            filtered.sort(key=lambda x: x["created_at"], reverse=True)
            limit = args.newest
        elif getattr(args, "sort", None) == "size":
            filtered.sort(key=lambda x: x["size"], reverse=not getattr(args, "reverse", False))
            limit = None if getattr(args, "all", False) else getattr(args, "limit", 50)
        elif getattr(args, "sort", None) == "name":
            filtered.sort(key=lambda x: x["name"].lower(), reverse=getattr(args, "reverse", False))
            limit = None if getattr(args, "all", False) else getattr(args, "limit", 50)
        else:
            filtered.sort(key=lambda x: x["created_at"], reverse=not getattr(args, "reverse", False))
            limit = None if getattr(args, "all", False) else getattr(args, "limit", 50)

        displayed = filtered[:limit] if limit else filtered

        if getattr(args, "json", False):
            print(json.dumps(displayed, indent=2))
            return

        total_b = sum(x["size"] for x in filtered)
        print(bold(f"\nFound {len(filtered)} matching files ({format_size(total_b)} total):"))
        if limit and len(filtered) > limit:
            print(gray(f"Showing top {limit} results:\n"))
        else:
            print()

        for it in displayed:
            icon = get_type_icon(it["name"])
            dt = it["created_at"][:10] if it["created_at"] else "          "
            print(f"  {icon}  {bold(format_size(it['size'])):>9}  {gray(dt)}  {cyan(it['folder_name']):<16}  {colorize_filename(it['name'])}")

        if limit and len(filtered) > limit:
            print(gray(f"\n... and {len(filtered) - limit} more matching files. (Use -a/--all to see all)."))
        print()

    except Exception as e:
        print(red(f"Error during find: {e}"))

def cmd_search(args: argparse.Namespace) -> None:
    """Smart fuzzy & token search across Telegram Drive archive."""
    if not args.query:
        print(yellow("Please specify a search query. Example: tg-backup search 'operating systems'"))
        return

    owner_id, folders = get_desktop_account_info()
    if not owner_id:
        print(red("No active account found in workspace."))
        return

    workspace_db = WORKSPACE_DIR / owner_id / "workspace.db"
    if not workspace_db.exists():
        print(red(f"workspace.db not found at {workspace_db}"))
        return

    try:
        conn = sqlite3.connect(str(workspace_db))
        items = parse_all_items(conn)
        conn.close()

        query = args.query.strip()
        scored_items = []
        for it in items:
            score = fuzzy_match(query, it["name"])
            if query.lower() in it["folder_name"].lower():
                score = max(score, 0.5)
            if score >= 0.3:
                scored_items.append((score, it))

        scored_items.sort(key=lambda x: (x[0], x[1]["created_at"]), reverse=True)

        if getattr(args, "folder", None):
            f_lower = args.folder.lower()
            scored_items = [x for x in scored_items if x[1]["folder_name"].lower() == f_lower]

        if getattr(args, "type", None):
            tf = args.type.lower().lstrip(".")
            if tf in CATEGORIES:
                scored_items = [x for x in scored_items if x[1]["category"] == tf]
            else:
                scored_items = [x for x in scored_items if x[1]["file_ext"].lstrip(".") == tf]

        limit = None if getattr(args, "all", False) else getattr(args, "limit", 50)
        displayed = scored_items[:limit] if limit else scored_items

        if getattr(args, "json", False):
            out = [{"score": round(score, 2), **it} for score, it in displayed]
            print(json.dumps(out, indent=2))
            return

        if not scored_items:
            print(yellow(f"\nNo files matched '{query}'. Try broader terms or check spelling.\n"))
            return

        print(bold(f"\nFound {len(scored_items)} matches for '{cyan(query)}':\n"))
        for idx, (score, it) in enumerate(displayed, 1):
            icon = get_type_icon(it["name"])
            dt = it["created_at"][:10] if it["created_at"] else "Unknown"
            score_bar = f"{int(score * 100)}%"
            print(f"  {idx:>2}. {icon} {bold(colorize_filename(it['name']))}")
            print(f"      {cyan(it['folder_name'])}  ·  {green(format_size(it['size']))}  ·  {gray(dt)}  ·  Match: {gray(score_bar)}")

        if limit and len(scored_items) > limit:
            print(gray(f"\n... and {len(scored_items) - limit} more matches. (Use -a to view all)."))
        print()

    except Exception as e:
        print(red(f"Error during search: {e}"))

def cmd_duplicates(args: argparse.Namespace) -> None:
    """Detect duplicate files by filename and size in Telegram Drive archive."""
    owner_id, folders = get_desktop_account_info()
    if not owner_id:
        print(red("No active account found in workspace."))
        return

    workspace_db = WORKSPACE_DIR / owner_id / "workspace.db"
    if not workspace_db.exists():
        print(red(f"workspace.db not found at {workspace_db}"))
        return

    try:
        conn = sqlite3.connect(str(workspace_db))
        items = parse_all_items(conn)
        conn.close()

        # Group by normalized filename + size
        by_name_size = defaultdict(list)
        for it in items:
            key = (it["name"].strip().lower(), it["size"])
            by_name_size[key].append(it)

        # Also group by exact size (> 1MB) to spot potential renamed dupes
        by_size_only = defaultdict(list)
        for it in items:
            if it["size"] > 1024 * 1024:
                by_size_only[it["size"]].append(it)

        dupe_groups = [group for group in by_name_size.values() if len(group) > 1]
        dupe_groups.sort(key=lambda g: g[0]["size"] * (len(g) - 1), reverse=True)

        wasted_bytes = sum(g[0]["size"] * (len(g) - 1) for g in dupe_groups)

        if getattr(args, "json", False):
            out = []
            for g in dupe_groups:
                out.append({
                    "name": g[0]["name"],
                    "size": g[0]["size"],
                    "copies": len(g),
                    "wasted_bytes": g[0]["size"] * (len(g) - 1),
                    "files": g
                })
            print(json.dumps(out, indent=2))
            return

        print(bold("\n════ Duplicate File Analysis ════"))
        if not dupe_groups:
            print(green("  No duplicate files detected by name and size!"))
            print()
            return

        total_dupe_files = sum(len(g) for g in dupe_groups)
        print(f"  Found {red(str(len(dupe_groups)))} duplicate groups ({total_dupe_files} files total)")
        print(f"  Estimated reclaimable cloud space: {bold(green(format_size(wasted_bytes)))}\n")

        for idx, group in enumerate(dupe_groups, 1):
            sample = group[0]
            icon = get_type_icon(sample["name"])
            wasted = sample["size"] * (len(group) - 1)
            print(bold(f"  Group #{idx}: {icon} {sample['name']}"))
            print(f"  Copies: {yellow(str(len(group)))}  ·  Each: {format_size(sample['size'])}  ·  Wasted: {red(format_size(wasted))}")
            for it in group:
                dt = it["created_at"][:16] if it["created_at"] else "Unknown"
                print(f"    - {cyan(it['folder_name']):<18}  {gray(dt)}  (ID: {it['id'] or 'N/A'})")
            print()

        same_size_candidates = [
            g for g in by_size_only.values()
            if len(g) > 1 and len(set(x["name"].strip().lower() for x in g)) > 1
        ]
        if same_size_candidates:
            print(gray("── Note: Potential Renamed Candidates (identical exact byte size): ──"))
            for g in same_size_candidates[:5]:
                print(f"  Size {bold(format_size(g[0]['size']))}:")
                for it in g:
                    print(f"    • {it['name']} ({it['folder_name']})")
            print()

    except Exception as e:
        print(red(f"Error analyzing duplicates: {e}"))

def cmd_groups(args: argparse.Namespace) -> None:
    """Detect multipart archives, numbered lecture series, and related file clusters."""
    owner_id, folders = get_desktop_account_info()
    if not owner_id:
        print(red("No active account found in workspace."))
        return

    workspace_db = WORKSPACE_DIR / owner_id / "workspace.db"
    if not workspace_db.exists():
        print(red(f"workspace.db not found at {workspace_db}"))
        return

    try:
        conn = sqlite3.connect(str(workspace_db))
        items = parse_all_items(conn)
        conn.close()

        # 1. Detect multipart archives
        multipart_patterns = [
            r'^(.*?)\.part(\d+)\.(rar|zip|7z)$',
            r'^(.*?)\.r(\d{2})$',
            r'^(.*?)\.z(\d{2})$',
        ]
        multipart_groups = defaultdict(list)
        claimed_keys = set()

        for it in items:
            for pat in multipart_patterns:
                m = re.match(pat, it["name"], re.IGNORECASE)
                if m:
                    base_name = m.group(1)
                    multipart_groups[base_name].append(it)
                    claimed_keys.add(it["key"])
                    break

        # 2. Detect paired files (e.g. 47.pdf and 47.mp4)
        stem_groups = defaultdict(list)
        for it in items:
            stem = Path(it["name"]).stem
            stem_groups[stem].append(it)

        paired_groups = {}
        for stem, g in stem_groups.items():
            if len(g) >= 2:
                exts = set(x["file_ext"] for x in g)
                if len(exts) >= 2 and all(x["key"] not in claimed_keys for x in g):
                    paired_groups[stem] = g

        # 3. Detect numbered series
        series_patterns = [
            (r'^(Day[\s\-_]*\d+)', "Day Series"),
            (r'^(\d+\.\d+)', "Lecture Sections"),
            (r'^(Section\s*[\d\w]+)', "Course Sections"),
            (r'^(\d{1,2})\.(pdf|mp4)', "Numbered Lectures"),
        ]
        series_clusters = defaultdict(list)
        for it in items:
            if it["key"] in claimed_keys:
                continue
            for pat, series_name in series_patterns:
                m = re.search(pat, it["name"], re.IGNORECASE)
                if m:
                    series_clusters[series_name].append(it)
                    break

        if getattr(args, "json", False):
            out = {
                "multipart_archives": [
                    {"name": k, "files_count": len(v), "total_size": sum(x["size"] for x in v), "files": v}
                    for k, v in multipart_groups.items()
                ],
                "paired_files": [
                    {"stem": k, "files_count": len(v), "total_size": sum(x["size"] for x in v), "files": v}
                    for k, v in paired_groups.items() if len(v) <= 5
                ],
                "series": [
                    {"series": k, "files_count": len(v), "total_size": sum(x["size"] for x in v), "files": v}
                    for k, v in series_clusters.items()
                ]
            }
            print(json.dumps(out, indent=2))
            return

        print(bold("\n════ Smart Archive & Series Groups ════"))

        # Section 1: Multipart Archives
        if multipart_groups:
            print(bold(f"\n📦 Multipart Archives ({len(multipart_groups)} sets detected):"))
            for base, g in multipart_groups.items():
                tot = sum(x["size"] for x in g)
                print(f"  • {bold(base)} ({len(g)} parts, {green(format_size(tot))})")
                for it in sorted(g, key=lambda x: x["name"]):
                    print(f"      - {it['name']} ({format_size(it['size'])})")

        # Section 2: Numbered Series
        if series_clusters:
            print(bold(f"\n📚 Course & Lecture Series:"))
            for s_name, g in series_clusters.items():
                tot = sum(x["size"] for x in g)
                print(f"  • {bold(s_name)} ({len(g)} files, {green(format_size(tot))})")
                if len(g) > 6:
                    for it in g[:3]:
                        print(f"      - {it['name']} ({format_size(it['size'])})")
                    print(f"      {gray(f'... and {len(g) - 5} more files ...')}")
                    for it in g[-2:]:
                        print(f"      - {it['name']} ({format_size(it['size'])})")
                else:
                    for it in g:
                        print(f"      - {it['name']} ({format_size(it['size'])})")

        # Section 3: Paired Materials
        note_video_pairs = {k: v for k, v in paired_groups.items() if any(x["file_ext"] in [".pdf", ".docx"] for x in v) and any(x["file_ext"] in [".mp4", ".mkv"] for x in v)}
        if note_video_pairs:
            print(bold(f"\n🔗 Paired Materials (Document + Video Pairs):"))
            print(f"  Detected {len(note_video_pairs)} pairs (lecture PDF + matching video):")
            sample_pairs = list(note_video_pairs.items())[:6]
            for stem, g in sample_pairs:
                tot = sum(x["size"] for x in g)
                exts_str = ", ".join(x["file_ext"] for x in g)
                print(f"  • {bold(stem)} [{exts_str}] ({format_size(tot)})")
            if len(note_video_pairs) > 6:
                print(gray(f"  ... and {len(note_video_pairs) - 6} more paired files."))

        print()

    except Exception as e:
        print(red(f"Error detecting groups: {e}"))

def cmd_ls(args: argparse.Namespace) -> None:
    """List indexed files from Telegram Drive workspace with grouped or flat view."""
    owner_id, folders = get_desktop_account_info()
    if not owner_id:
        print(red("No active account found in workspace."))
        return

    workspace_db = WORKSPACE_DIR / owner_id / "workspace.db"
    if not workspace_db.exists():
        print(red(f"workspace.db not found at {workspace_db}"))
        return

    try:
        conn = sqlite3.connect(str(workspace_db))

        # Query folder breakdown
        folder_stats = conn.execute(
            "SELECT folder_name, COUNT(*) FROM workspace_files GROUP BY folder_name"
        ).fetchall()

        # If user just wants folders (-d / --folders)
        if getattr(args, "folders", False):
            if args.json:
                print(json.dumps([{"folder": r[0], "count": r[1]} for r in folder_stats], indent=2))
                conn.close()
                return
            print(bold("\n=== Telegram Drive Folders / Channels ==="))
            for fname, cnt in folder_stats:
                print(f"  {blue('drwx------')}  {cnt:>5} files   {cyan(fname + '/')}")
            print()
            conn.close()
            return

        target = getattr(args, "target", None) or getattr(args, "query", None)
        folder_filter = getattr(args, "folder", None)

        # Check if target is a known folder
        known_folder_names = {r[0].lower(): r[0] for r in folder_stats}
        if target and target.lower() in known_folder_names:
            folder_filter = known_folder_names[target.lower()]
            target = None

        where_clauses = []
        params = []
        if folder_filter:
            where_clauses.append("LOWER(folder_name) = LOWER(?)")
            params.append(folder_filter)
        if target:
            where_clauses.append("metadata LIKE ?")
            params.append(f"%{target}%")

        items = parse_all_items(conn, where_clauses, params)
        conn.close()

        if not items:
            print(yellow(f"No files found matching criteria."))
            return

        # Type filter if provided
        type_filter = getattr(args, "type", None)
        if type_filter:
            tf = type_filter.lower().lstrip(".")
            if tf in CATEGORIES:
                items = [x for x in items if x["category"] == tf]
            else:
                items = [x for x in items if x["file_ext"].lstrip(".") == tf]

        if not items:
            print(yellow(f"No files found for type '{type_filter}'."))
            return

        # Sorting
        sort_by = getattr(args, "sort", "date")
        reverse = getattr(args, "reverse", False)

        if sort_by == "size":
            items.sort(key=lambda x: x["size"], reverse=not reverse)
        elif sort_by == "name":
            items.sort(key=lambda x: x["name"].lower(), reverse=reverse)
        else: # date
            items.sort(key=lambda x: x["created_at"], reverse=not reverse)

        # Limit
        limit = None if getattr(args, "all", False) else getattr(args, "limit", 50)
        displayed_items = items[:limit] if limit else items

        if args.json:
            print(json.dumps(displayed_items, indent=2))
            return

        total_bytes = sum(x["size"] for x in items)
        header_folder = f" in '{cyan(folder_filter)}'" if folder_filter else ""
        print(bold(f"\nListing {len(displayed_items)} of {len(items)} files{header_folder} ({format_size(total_bytes)} total):"))

        # Determine grouping: default is "folder", unless --flat or --group type/none
        use_flat = getattr(args, "flat", False) or getattr(args, "group", "folder") in ("none", "flat")
        group_by_type = getattr(args, "group", "folder") == "type"

        if use_flat:
            # Flat tabular output
            col_type = 9
            col_size = 10
            col_date = 16
            col_folder = 16

            print()
            print(bold(f"{'TYPE':<{col_type}}  {'SIZE':>{col_size}}  {'MODIFIED':<{col_date}}  {'FOLDER':<{col_folder}}  {'NAME'}"))
            print("-" * 90)

            for item in displayed_items:
                enc = item["encryption_state"]
                icon = get_type_icon(item["name"])
                raw_type = f"{icon} plain" if enc == "plain" else f"{icon} enc2"
                type_str = gray(raw_type) if enc == "plain" else green(raw_type)

                raw_size = format_size(item["size"])
                size_str = raw_size.rjust(col_size)

                raw_date = item["created_at"][:16] if item["created_at"] else " " * col_date
                date_str = gray(raw_date.ljust(col_date))

                raw_folder = item["folder_name"][:col_folder]
                folder_str = cyan(raw_folder.ljust(col_folder))

                fname_colored = colorize_filename(item["name"])
                print(f"{type_str}  {size_str}  {date_str}  {folder_str}  {fname_colored}")

        elif group_by_type:
            # Grouped by category
            groups = defaultdict(list)
            for it in displayed_items:
                groups[it["category"]].append(it)

            ordered_cats = ["documents", "media", "archives", "code", "images", "data", "configs", "other"]
            for cat in ordered_cats:
                flist = groups.get(cat, [])
                if not flist:
                    continue
                g_bytes = sum(x["size"] for x in flist)
                icon = TYPE_ICONS.get(cat, "📁")
                print(bold(f"\n{icon} {cat.capitalize()} ({len(flist)} files, {format_size(g_bytes)}):"))
                for it in flist:
                    dt = it["created_at"][:10] if it["created_at"] else "          "
                    print(f"    {bold(format_size(it['size'])):>9}  {gray(dt)}  {cyan(it['folder_name']):<16}  {colorize_filename(it['name'])}")

        else:
            # Grouped by folder (default)
            groups = defaultdict(list)
            for it in displayed_items:
                groups[it["folder_name"]].append(it)

            for fname, flist in sorted(groups.items()):
                g_bytes = sum(x["size"] for x in flist)
                print(bold(f"\n📁 {fname}/ ({len(flist)} files, {format_size(g_bytes)}):"))
                for it in flist:
                    icon = get_type_icon(it["name"])
                    dt = it["created_at"][:10] if it["created_at"] else "          "
                    print(f"    {icon}  {bold(format_size(it['size'])):>9}  {gray(dt)}  {colorize_filename(it['name'])}")

        if limit and len(items) > limit:
            print(gray(f"\n... and {len(items) - limit} more files. (Use 'tg-backup ls -a' to view all)."))
        print()

    except Exception as e:
        print(red(f"Error querying workspace.db: {e}"))

cmd_list = cmd_ls


def cmd_backup(args: argparse.Namespace) -> None:
    """Perform organized file/folder backup to Telegram Drive."""
    target_path = Path(args.path).resolve()
    if not target_path.exists():
        print(red(f"Error: Path does not exist: {target_path}"))
        return

    owner_id, folders = get_desktop_account_info()
    if not owner_id:
        print(red("Error: Telegram Drive account not found. Please log in to Telegram Drive desktop app first."))
        return

    # Resolve folder ID
    target_folder_id = None
    target_folder_name = "Saved Messages"
    if args.folder:
        for f in folders:
            if str(f.get("id")) == str(args.folder) or f.get("name", "").lower() == str(args.folder).lower():
                target_folder_id = f.get("id")
                target_folder_name = f.get("name")
                break
        if target_folder_id is None:
            # Check if integer ID provided directly
            if str(args.folder).isdigit():
                target_folder_id = int(args.folder)
                target_folder_name = f"Channel {target_folder_id}"
            else:
                print(yellow(f"Warning: Folder '{args.folder}' not found. Defaulting to Saved Messages."))
    elif folders:
        # Default to first configured channel folder (e.g. DM) if available
        target_folder_id = folders[0].get("id")
        target_folder_name = folders[0].get("name")

    print(bold("\n=== Telegram Drive Backup ==="))
    print(f"  Source:      {cyan(str(target_path))}")
    print(f"  Destination: {green(target_folder_name)} (ID: {target_folder_id or 'None'})")
    print(f"  Account ID:  {owner_id}")

    # Mode 1: Compressed Archive Mode
    if args.archive or args.compress:
        backup_name = args.name or f"Backup_{target_path.name}_{time.strftime('%Y%m%d_%H%M%S')}"
        archive_format = "7z" if args.format == "7z" and SEVEN_ZIP.exists() else "zip"
        temp_dir = Path(tempfile.gettempdir()) / "antigravity_backups"
        temp_dir.mkdir(parents=True, exist_ok=True)
        archive_path = temp_dir / f"{backup_name}.{archive_format}"

        print(f"\nCreating organized compressed archive ({archive_format.upper()})...")

        # Collect files
        files_to_pack = collect_files(target_path, recursive=True)
        print(f"Collected {bold(str(len(files_to_pack)))} files.")

        if args.dry_run:
            total_size = sum(f.stat().st_size for f in files_to_pack)
            print(f"{yellow('[DRY RUN]')} Would archive {len(files_to_pack)} files ({format_size(total_size)}) into {archive_path.name}")
            return

        # Create Manifest
        manifest = {
            "backup_name": backup_name,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_path": str(target_path),
            "target_folder": target_folder_name,
            "target_folder_id": target_folder_id,
            "file_count": len(files_to_pack),
            "files": []
        }

        # Build archive using 7z if available
        if archive_format == "7z" and SEVEN_ZIP.exists():
            cmd = [str(SEVEN_ZIP), "a", str(archive_path), f"{str(target_path)}\\*"]
            for exc in DEFAULT_EXCLUDES:
                cmd.append(f"-xr!{exc}")
            cmd.extend(["-mx=5", "-bso0"]) # Fast compression, silent standard output
            subprocess.run(cmd, check=True)
        else:
            # Python zipfile fallback
            import zipfile
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in files_to_pack:
                    rel = f.relative_to(target_path) if target_path.is_dir() else f.name
                    zf.write(f, arcname=str(rel))

        archive_size = archive_path.stat().st_size
        print(f"Archive created: {cyan(archive_path.name)} ({format_size(archive_size)})")

        # Enqueue archive
        print("Enqueuing to Telegram Drive transfer queue...")
        ok, job_id = enqueue_upload_job(
            file_path=archive_path,
            owner_id=owner_id,
            folder_id=target_folder_id,
            custom_filename=archive_path.name
        )
        if ok:
            print(f"{green(SYM_OK)} Successfully queued job: {bold(job_id)}")
            if not is_app_running():
                print(yellow("Notice: Telegram Drive app is not currently running. Starting it now..."))
                start_desktop_app()
            print(gray("Run 'tg-backup status' or 'tg-backup watch' to monitor progress."))
        else:
            print(red(f"Failed to queue archive: {job_id}"))
        return

    # Mode 2: Organized Individual Files Mode
    files_to_backup = collect_files(target_path, recursive=not args.no_recurse)
    if not files_to_backup:
        print(yellow("No files found matching backup criteria."))
        return

    # Group by category
    categorized: Dict[str, List[Path]] = {}
    for f in files_to_backup:
        cat = get_file_category(f)
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append(f)

    total_bytes = sum(f.stat().st_size for f in files_to_backup)
    print(f"\nFound {bold(str(len(files_to_backup)))} files ({format_size(total_bytes)}):")
    for cat, flist in sorted(categorized.items()):
        c_bytes = sum(f.stat().st_size for f in flist)
        print(f"  - {bold(cat.capitalize()):<12} {len(flist):>4} files ({format_size(c_bytes)})")

    if args.dry_run:
        print(f"\n{yellow('[DRY RUN]')} No files were queued. Use without --dry-run to execute backup.")
        return

    print("\nEnqueuing files to Telegram Drive...")
    queued_count = 0
    errors = 0

    for f in files_to_backup:
        # Naming format: optional prefix with category or project
        filename = f.name
        if args.organize == "category":
            cat = get_file_category(f)
            filename = f"[{cat}] {f.name}"
        elif args.organize == "prefix" and args.name:
            filename = f"{args.name}_{f.name}"

        ok, job_id = enqueue_upload_job(
            file_path=f,
            owner_id=owner_id,
            folder_id=target_folder_id,
            custom_filename=filename
        )
        if ok:
            queued_count += 1
        else:
            errors += 1
            print(red(f"Error enqueuing {f.name}: {job_id}"))

    print(f"\n{green(SYM_OK)} Enqueued {bold(str(queued_count))} files into Telegram Drive queue.")
    if errors:
        print(f"{red(SYM_ERR)} Encountered {errors} errors.")

    if not is_app_running():
        print(yellow("Notice: Telegram Drive app is not currently running. Starting it now to process transfers..."))
        start_desktop_app()

    print(gray("Run 'tg-backup status' to check queue or 'tg-backup watch' to follow live progress.\n"))

def cmd_watch(args: argparse.Namespace) -> None:
    """Live terminal monitor for Telegram Drive transfer queue."""
    if not TRANSFERS_DB.exists():
        print(red("Error: transfers.db not found."))
        return

    print("Watching Telegram Drive transfers (Press Ctrl+C to exit)...")
    try:
        while True:
            conn = sqlite3.connect(str(TRANSFERS_DB))
            rows = conn.execute(
                "SELECT id, status, payload_json FROM transfer_jobs WHERE status IN ('pending', 'active') ORDER BY queue_position ASC"
            ).fetchall()
            completed_count = conn.execute("SELECT COUNT(*) FROM transfer_jobs WHERE status='completed'").fetchone()[0]
            failed_count = conn.execute("SELECT COUNT(*) FROM transfer_jobs WHERE status='failed'").fetchone()[0]
            conn.close()

            sys.stdout.write("\033[2J\033[H") # Clear terminal screen
            print(bold("=== Telegram Drive Live Transfer Monitor ==="))
            print(f"Completed: {green(str(completed_count))} | Active/Pending: {yellow(str(len(rows)))} | Failed: {red(str(failed_count))}")
            print("-" * 65)

            if not rows:
                print(green("\nAll active and pending transfers have completed!"))
                break

            for r in rows[:10]:
                job_id, status, payload_raw = r
                p = json.loads(payload_raw)
                fname = p.get("filename", "Unknown")[:30]
                prog = p.get("progress", 0)
                bar_len = 20
                filled = int(bar_len * (prog / 100))
                bar = "[" + "=" * filled + " " * (bar_len - filled) + "]"
                speed = format_size(p.get("speedBytesPerSec", 0)) + "/s"
                print(f"{job_id} {bar} {prog:>3}% ({speed}) {status:<8} {fname}")

            time.sleep(2)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

# --- CLI Setup ---

def main():
    parser = argparse.ArgumentParser(
        prog="tg-backup",
        description="Advanced Terminal Backup Tool for Telegram Drive"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # backup command
    p_backup = subparsers.add_parser("backup", help="Backup a file or folder to Telegram Drive")
    p_backup.add_argument("path", help="Path of directory or file to back up")
    p_backup.add_argument("--folder", "-f", help="Target Telegram folder ID or name (default: DM / Saved Messages)")
    p_backup.add_argument("--name", "-n", help="Custom backup snapshot name")
    p_backup.add_argument("--archive", "-a", action="store_true", help="Compress files into a single snapshot archive")
    p_backup.add_argument("--compress", "-c", action="store_true", help="Alias for --archive")
    p_backup.add_argument("--format", choices=["7z", "zip"], default="zip", help="Archive format (default: zip)")
    p_backup.add_argument("--organize", choices=["category", "prefix", "flat"], default="category", help="File organization method")
    p_backup.add_argument("--no-recurse", action="store_true", help="Do not back up subdirectories recursively")
    p_backup.add_argument("--dry-run", action="store_true", help="Preview backup plan without executing")

    # status command
    p_status = subparsers.add_parser("status", help="Show current transfer queue status")
    p_status.add_argument("--limit", "-l", type=int, default=15, help="Number of records to show")
    p_status.add_argument("--json", action="store_true", help="Output JSON format")

    # watch command
    p_watch = subparsers.add_parser("watch", help="Live watch queue until all transfers complete")

    # ls / list command
    for cmd_name in ["ls", "list"]:
        p_ls = subparsers.add_parser(cmd_name, help="List/browse backed up files (grouped by folder or flat)")
        p_ls.add_argument("target", nargs="?", help="Optional folder name (e.g. DM) or search query")
        p_ls.add_argument("--folder", "-f", help="Filter by specific Telegram folder")
        p_ls.add_argument("--type", "-t", help="Filter by file category (documents, media, archives, code) or extension (pdf, mp4)")
        p_ls.add_argument("--folders", "-d", action="store_true", help="List folders/channels only")
        p_ls.add_argument("--group", choices=["folder", "type", "none"], default="folder", help="Grouping mode: folder, type, none (default: folder)")
        p_ls.add_argument("--flat", action="store_true", help="Display as classic flat table without folder grouping")
        p_ls.add_argument("--sort", "-s", choices=["date", "size", "name"], default="date", help="Sort order (default: date)")
        p_ls.add_argument("--reverse", "-r", action="store_true", help="Reverse sort order")
        p_ls.add_argument("--all", "-a", action="store_true", help="List all files without truncation")
        p_ls.add_argument("--limit", "-l", type=int, default=50, help="Max results to display (default: 50)")
        p_ls.add_argument("--json", action="store_true", help="Output JSON format")

    # stats command
    p_stats = subparsers.add_parser("stats", help="Show rich archive analytics and statistics")
    p_stats.add_argument("--top", "-t", type=int, default=5, help="Number of largest files to display (default: 5)")
    p_stats.add_argument("--json", action="store_true", help="Output JSON format")

    # find command
    p_find = subparsers.add_parser("find", help="Discover files using composable filters")
    p_find.add_argument("query", nargs="?", help="Optional filename filter pattern")
    p_find.add_argument("--type", "-t", help="File category (documents, media, archives, code) or extension (pdf, mp4)")
    p_find.add_argument("--ext", help="Exact file extension (e.g. .pdf, .zip)")
    p_find.add_argument("--min-size", help="Minimum file size threshold (e.g. 100MB, 1GB)")
    p_find.add_argument("--max-size", help="Maximum file size threshold (e.g. 50MB)")
    p_find.add_argument("--after", help="Filter files created on or after date (YYYY-MM-DD)")
    p_find.add_argument("--before", help="Filter files created on or before date (YYYY-MM-DD)")
    p_find.add_argument("--folder", "-f", help="Filter by folder name")
    p_find.add_argument("--largest", type=int, help="Show N largest matching files")
    p_find.add_argument("--newest", type=int, help="Show N newest matching files")
    p_find.add_argument("--sort", choices=["date", "size", "name"], default="date", help="Sort order")
    p_find.add_argument("--reverse", "-r", action="store_true", help="Reverse sort order")
    p_find.add_argument("--all", "-a", action="store_true", help="Show all results without limit")
    p_find.add_argument("--limit", "-l", type=int, default=50, help="Max results to display (default: 50)")
    p_find.add_argument("--json", action="store_true", help="Output JSON format")

    # search command
    p_search = subparsers.add_parser("search", help="Smart fuzzy & token search across archive")
    p_search.add_argument("query", help="Search query string (e.g. 'operating systems', 'react')")
    p_search.add_argument("--folder", "-f", help="Filter by folder name")
    p_search.add_argument("--type", "-t", help="Filter by category or extension")
    p_search.add_argument("--all", "-a", action="store_true", help="Show all matches")
    p_search.add_argument("--limit", "-l", type=int, default=50, help="Max results to display")
    p_search.add_argument("--json", action="store_true", help="Output JSON format")

    # duplicates command
    p_dupes = subparsers.add_parser("duplicates", aliases=["dupes"], help="Detect duplicate files and wasted cloud storage")
    p_dupes.add_argument("--json", action="store_true", help="Output JSON format")

    # groups command
    p_groups = subparsers.add_parser("groups", help="Detect multipart archives, lecture series, and paired files")
    p_groups.add_argument("--json", action="store_true", help="Output JSON format")

    # app command
    p_app = subparsers.add_parser("app", help="Manage Telegram Drive application")
    p_app.add_argument("action", choices=["status", "start", "stop"], help="Action to perform")

    # doctor command
    p_doctor = subparsers.add_parser("doctor", help="Inspect Telegram Drive health, paths, and toolchain")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "doctor":
        cmd_doctor(args)
    elif args.command == "app":
        cmd_app(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "watch":
        cmd_watch(args)
    elif args.command in ("ls", "list"):
        cmd_ls(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "find":
        cmd_find(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command in ("duplicates", "dupes"):
        cmd_duplicates(args)
    elif args.command == "groups":
        cmd_groups(args)
    elif args.command == "backup":
        cmd_backup(args)

if __name__ == "__main__":
    main()
