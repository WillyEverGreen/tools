"""
Pyright static type analyzer adapter for Python.
"""

import json
from pathlib import Path
from typing import List, Tuple, Optional
from .base import BaseAnalyzer, normalize_file_path
from ..ir import Diagnostic

class PyrightAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__("pyright")

    @property
    def name(self) -> str:
        return "pyright"

    @property
    def supported_languages(self) -> List[str]:
        return ["python"]

    def run(
        self,
        files: List[Path],
        fix: bool = False,
        cwd: Optional[Path] = None,
        timeout_sec: float = 60.0
    ) -> Tuple[List[Diagnostic], float]:
        if not self.is_available or not files:
            return [], 0.0

        run_cwd = cwd or Path.cwd()
        cmd = [self.executable_path, "--outputjson"]
        cmd.extend(str(f) for f in files)

        retcode, stdout, stderr, duration_ms = self._execute_process(cmd, run_cwd, timeout_sec)

        stdout = stdout.strip()
        if not stdout or not stdout.startswith("{"):
            return [], duration_ms

        diagnostics = []
        try:
            data = json.loads(stdout)
            for d in data.get("generalDiagnostics", []):
                fpath = d.get("file", "")
                norm_file = normalize_file_path(fpath, cwd=run_cwd)
                rng = d.get("range", {}).get("start", {})
                end_rng = d.get("range", {}).get("end", {})
                sev = d.get("severity", "error").lower()
                rule = d.get("rule") or "reportGeneralTypeIssues"

                diagnostics.append(Diagnostic(
                    severity=sev if sev in ("error", "warning") else "info",
                    category="type",
                    file=norm_file,
                    line=rng.get("line", 0) + 1,
                    column=rng.get("character", 0) + 1,
                    rule=rule,
                    message=d.get("message", ""),
                    tool=self.name,
                    fixable=False,
                    end_line=end_rng.get("line", 0) + 1,
                    end_column=end_rng.get("character", 0) + 1
                ))
        except Exception:
            pass

        return diagnostics, duration_ms
