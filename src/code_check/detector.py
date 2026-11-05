"""
Project and language detection, file collection, and Git incremental tracking.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple

PY_EXTENSIONS = {".py", ".pyi"}
TS_EXTENSIONS = {".ts", ".tsx", ".mts", ".cts"}
JS_EXTENSIONS = {".js", ".jsx", ".mjs", ".cjs"}
SUPPORTED_EXTENSIONS = PY_EXTENSIONS | TS_EXTENSIONS | JS_EXTENSIONS

DEFAULT_EXCLUDES = {
    "node_modules", ".git", ".venv", "venv", "env", "__pycache__",
    "dist", "build", ".next", ".turbo", "out", "target", ".gemini",
    ".cache", ".pytest_cache", ".ruff_cache", "coverage", ".coverage"
}

class ProjectDetector:
    """Detects active project languages and collects files for analysis."""

    def __init__(self, root: Path, custom_excludes: Optional[Set[str]] = None):
        self.root = root.resolve()
        self.excludes = set(DEFAULT_EXCLUDES)
        if custom_excludes:
            self.excludes.update(custom_excludes)

    def is_git_repo(self) -> bool:
        """Check if target directory is inside a Git working tree."""
        return (self.root / ".git").exists() or shutil_which_git(self.root)

    def get_git_changed_files(self) -> List[Path]:
        """Collect untracked, modified, and staged files using Git."""
        try:
            out = subprocess.check_output(
                ["git", "status", "--porcelain", "-uall"],
                cwd=str(self.root),
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            changed = []
            for line in out.splitlines():
                if not line or len(line) < 3:
                    continue
                # Status line format: XY path/to/file or XY "path with spaces" -> path
                raw_path = line[3:].strip().strip('"')
                if " -> " in raw_path:  # Handle renames: old -> new
                    raw_path = raw_path.split(" -> ", 1)[1].strip().strip('"')
                p = (self.root / raw_path).resolve()
                if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                    changed.append(p)
            return sorted(list(set(changed)))
        except Exception:
            return []

    def collect_files(self, paths: Optional[List[Path]] = None, changed_only: bool = False) -> List[Path]:
        """Collect supported files respecting exclusion rules."""
        if changed_only:
            return self.get_git_changed_files()

        targets = paths or [self.root]
        collected = []

        for target in targets:
            target = target.resolve()
            if target.is_file():
                if target.suffix.lower() in SUPPORTED_EXTENSIONS:
                    collected.append(target)
            elif target.is_dir():
                for root, dirs, fnames in os.walk(target):
                    # Prune excluded directories
                    dirs[:] = [
                        d for d in dirs
                        if d not in self.excludes and not d.startswith(".")
                    ]
                    for fn in fnames:
                        ext = Path(fn).suffix.lower()
                        if ext in SUPPORTED_EXTENSIONS:
                            collected.append(Path(root) / fn)

        return sorted(list(set(collected)))

    def partition_by_language(self, files: List[Path]) -> Dict[str, List[Path]]:
        """Group files by language ecosystem for targeted analyzer dispatch."""
        partitioned: Dict[str, List[Path]] = {
            "python": [],
            "typescript": [],
            "javascript": [],
            "all_js_ts": []
        }
        for f in files:
            ext = f.suffix.lower()
            if ext in PY_EXTENSIONS:
                partitioned["python"].append(f)
            elif ext in TS_EXTENSIONS:
                partitioned["typescript"].append(f)
                partitioned["javascript"].append(f)
                partitioned["all_js_ts"].append(f)
            elif ext in JS_EXTENSIONS:
                partitioned["javascript"].append(f)
                partitioned["all_js_ts"].append(f)

        return partitioned

    def detect_languages(self) -> Dict[str, bool]:
        """Detect which language ecosystems are active in the project root."""
        has_py = self.has_pyproject() or any(self.root.glob("*.py"))
        has_ts = self.has_tsconfig() or any(self.root.glob("*.ts")) or any(self.root.glob("*.tsx"))
        has_js = (self.root / "package.json").exists() or any(self.root.glob("*.js")) or any(self.root.glob("*.jsx"))
        return {
            "python": has_py,
            "typescript": has_ts,
            "javascript": has_js
        }

    def has_tsconfig(self) -> bool:
        """Check if project contains TypeScript configuration."""
        return (self.root / "tsconfig.json").exists()

    def has_pyproject(self) -> bool:
        """Check if project contains Python configuration."""
        return (
            (self.root / "pyproject.toml").exists() or
            (self.root / "requirements.txt").exists() or
            (self.root / "setup.py").exists()
        )

def shutil_which_git(cwd: Path) -> bool:
    """Helper to verify Git is functional inside cwd."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(cwd),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return res.returncode == 0
    except Exception:
        return False
