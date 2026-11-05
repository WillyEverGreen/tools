"""
Ruff static analysis adapter for Python linting, correctness, and import checks.
"""

import json
from pathlib import Path
from typing import List, Tuple, Optional
from .base import BaseAnalyzer, normalize_file_path
from ..ir import Diagnostic

class RuffAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__("ruff")

    @property
    def name(self) -> str:
        return "ruff"

    @property
    def supported_languages(self) -> List[str]:
        return ["python"]

    def run(
        self,
        files: List[Path],
        fix: bool = False,
        cwd: Optional[Path] = None,
        timeout_sec: float = 30.0
    ) -> Tuple[List[Diagnostic], float]:
        if not self.is_available or not files:
            return [], 0.0

        run_cwd = cwd or Path.cwd()
        cmd = [self.executable_path, "check", "--output-format", "json"]
        if fix:
            cmd.append("--fix")
        cmd.extend(str(f) for f in files)

        retcode, stdout, stderr, duration_ms = self._execute_process(cmd, run_cwd, timeout_sec)

        stdout = stdout.strip()
        if not stdout or not stdout.startswith("["):
            return [], duration_ms

        diagnostics = []
        try:
            data = json.loads(stdout)
            for item in data:
                code = item.get("code", "Ruff")
                msg = item.get("message", "Lint issue")
                fname = item.get("filename", "")
                loc = item.get("location", {})
                end_loc = item.get("end_location", {})
                fix_obj = item.get("fix")

                norm_file = normalize_file_path(fname, cwd=run_cwd)

                # Map Ruff rules to unified categories
                category = "bug"
                if code.startswith(("F9", "E9")):
                    category = "syntax"
                elif code.startswith(("F", "B", "PLR", "PLE")):
                    category = "bug"
                elif code.startswith(("E", "W", "I", "UP", "C", "D", "Q", "RUF")):
                    category = "style"
                elif code.startswith("S"):
                    category = "security"
                elif code.startswith("PERF"):
                    category = "performance"

                severity = "error" if code.startswith(("F", "E9")) else "warning"

                diagnostics.append(Diagnostic(
                    severity=severity,
                    category=category,
                    file=norm_file,
                    line=loc.get("row", 1),
                    column=loc.get("column", 1),
                    rule=code,
                    message=msg,
                    tool=self.name,
                    fixable=bool(fix_obj),
                    end_line=end_loc.get("row"),
                    end_column=end_loc.get("column"),
                    url=item.get("url")
                ))
        except Exception:
            pass

        return diagnostics, duration_ms
