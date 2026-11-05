"""
Base interface and execution abstractions for analyzer adapters.
"""

import os
import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple, Optional
from ..ir import Diagnostic

TOOLS_DIR = Path(r"C:\tools")

def resolve_binary(binary_name: str) -> Optional[str]:
    """Resolve executable path, prioritizing C:\\tools followed by system PATH."""
    for ext in [".exe", ".cmd", ".bat", ""]:
        cand = TOOLS_DIR / f"{binary_name}{ext}"
        if cand.exists():
            return str(cand)
    if os.name == "nt":
        for ext in [".exe", ".cmd", ".bat"]:
            w = shutil.which(f"{binary_name}{ext}")
            if w:
                return w
    return shutil.which(binary_name)

def normalize_file_path(path_str: str, cwd: Optional[Path] = None) -> str:
    """Normalize file path to clean relative POSIX path when inside cwd."""
    p = Path(path_str)
    if cwd:
        try:
            p_resolved = p.resolve()
            cwd_resolved = cwd.resolve()
            if p_resolved.is_relative_to(cwd_resolved):
                return p_resolved.relative_to(cwd_resolved).as_posix()
        except Exception:
            pass
    return p.as_posix()

class BaseAnalyzer(ABC):
    """Abstract base class for static analysis tool adapters."""

    def __init__(self, binary_name: str):
        self.binary_name = binary_name
        self.executable_path = resolve_binary(binary_name)

    @property
    def is_available(self) -> bool:
        """Check if analyzer binary is installed and executable."""
        return self.executable_path is not None

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier name for this analyzer (e.g. 'ruff', 'oxlint')."""
        pass

    @property
    @abstractmethod
    def supported_languages(self) -> List[str]:
        """Languages processed by this analyzer (e.g. ['python'], ['typescript'])."""
        pass

    def get_version(self) -> Optional[str]:
        """Query analyzer executable for its version string."""
        if not self.is_available:
            return None
        try:
            cmd = [self.executable_path, "--version"]
            ret, stdout, stderr, _ = self._execute_process(cmd, Path.cwd(), timeout_sec=5.0)
            if ret == 0:
                raw = stdout.strip() or stderr.strip()
                if raw:
                    return raw.splitlines()[0].strip()
        except Exception:
            pass
        return None

    @abstractmethod
    def run(
        self,
        files: List[Path],
        fix: bool = False,
        cwd: Optional[Path] = None,
        timeout_sec: float = 30.0
    ) -> Tuple[List[Diagnostic], float]:
        """Run analysis on files and return normalized diagnostics with duration in ms."""
        pass

    def _execute_process(
        self,
        cmd: List[str],
        cwd: Path,
        timeout_sec: float = 30.0
    ) -> Tuple[int, str, str, float]:
        """Safely execute analyzer command via subprocess argument array."""
        t0 = time.perf_counter()
        try:
            # On Windows, .cmd and .bat require shell=True
            use_shell = os.name == "nt" and cmd[0].lower().endswith((".cmd", ".bat"))
            proc = subprocess.run(
                cmd,
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_sec,
                shell=use_shell
            )
            duration_ms = (time.perf_counter() - t0) * 1000
            return proc.returncode, proc.stdout, proc.stderr, duration_ms
        except subprocess.TimeoutExpired:
            duration_ms = (time.perf_counter() - t0) * 1000
            return 2, "", f"Execution timed out after {timeout_sec}s", duration_ms
        except Exception as e:
            duration_ms = (time.perf_counter() - t0) * 1000
            return 2, "", str(e), duration_ms
