"""
TypeScript compiler (tsc --noEmit) type checker adapter.
"""

import re
from pathlib import Path
from typing import List, Tuple, Optional
from .base import BaseAnalyzer, normalize_file_path
from ..ir import Diagnostic

TSC_ERROR_RE = re.compile(r'^(.*?)\((\d+),(\d+)\):\s+(error|warning)\s+(TS\d+):\s+(.*)$')

class TscAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__("tsc")

    @property
    def name(self) -> str:
        return "tsc"

    @property
    def supported_languages(self) -> List[str]:
        return ["typescript"]

    def run(
        self,
        files: List[Path],
        fix: bool = False,
        cwd: Optional[Path] = None,
        timeout_sec: float = 60.0
    ) -> Tuple[List[Diagnostic], float]:
        if not self.is_available:
            return [], 0.0

        run_cwd = cwd or Path.cwd()
        # Only run if tsconfig.json is present
        if not (run_cwd / "tsconfig.json").exists():
            return [], 0.0

        cmd = [self.executable_path, "--noEmit", "--pretty", "false"]
        retcode, stdout, stderr, duration_ms = self._execute_process(cmd, run_cwd, timeout_sec)

        allowed_files = {f.resolve() for f in files} if files else None

        diagnostics = []
        for line in stdout.splitlines():
            line = line.strip()
            m = TSC_ERROR_RE.match(line)
            if m:
                fpath, l_num, c_num, sev, code, msg = m.groups()
                norm_file = normalize_file_path(fpath, cwd=run_cwd)

                if allowed_files:
                    resolved = (run_cwd / fpath).resolve()
                    if resolved not in allowed_files:
                        continue

                diagnostics.append(Diagnostic(
                    severity=sev.lower(),
                    category="type",
                    file=norm_file,
                    line=int(l_num),
                    column=int(c_num),
                    rule=code,
                    message=msg,
                    tool=self.name,
                    fixable=False
                ))

        return diagnostics, duration_ms
