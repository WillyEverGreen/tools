"""
ESLint static analysis adapter for JavaScript, TypeScript, and React frameworks.
"""

import json
from pathlib import Path
from typing import List, Tuple, Optional
from .base import BaseAnalyzer, normalize_file_path
from ..ir import Diagnostic

class EslintAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__("eslint")

    @property
    def name(self) -> str:
        return "eslint"

    @property
    def supported_languages(self) -> List[str]:
        return ["javascript", "typescript"]

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

        # Check if project or subdirectories have eslint config
        has_config = (
            any(run_cwd.glob("eslint.config.*")) or
            any(run_cwd.glob(".eslintrc*")) or
            any(run_cwd.glob("*/eslint.config.*")) or
            any(run_cwd.glob("*/.eslintrc*"))
        )
        if not has_config:
            return [], 0.0

        # Run eslint with json formatter
        cmd = [self.executable_path, "-f", "json"]
        if fix:
            cmd.append("--fix")

        # Filter only JS/TS files
        target_files = [str(f) for f in files if f.suffix.lower() in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}]
        if not target_files:
            return [], 0.0

        cmd.extend(target_files)

        retcode, stdout, stderr, duration_ms = self._execute_process(cmd, run_cwd, timeout_sec)

        stdout = stdout.strip()
        if not stdout or not stdout.startswith("["):
            return [], duration_ms

        diagnostics: List[Diagnostic] = []
        try:
            data = json.loads(stdout)
            if isinstance(data, list):
                for file_entry in data:
                    fpath = file_entry.get("filePath", "")
                    norm_file = normalize_file_path(fpath, cwd=run_cwd)
                    for m in file_entry.get("messages", []):
                        rule = m.get("ruleId") or "eslint"
                        sev_num = m.get("severity", 2)
                        severity = "error" if sev_num == 2 else "warning"

                        category = "bug" if severity == "error" else "style"
                        rule_lower = rule.lower()
                        if "security" in rule_lower:
                            category = "security"
                        elif "react" in rule_lower or "hook" in rule_lower or "typescript" in rule_lower:
                            category = "bug"
                        elif "perf" in rule_lower:
                            category = "performance"

                        diagnostics.append(Diagnostic(
                            severity=severity,
                            category=category,
                            file=norm_file,
                            line=m.get("line", 1),
                            column=m.get("column", 1),
                            rule=rule,
                            message=m.get("message", ""),
                            tool=self.name,
                            fixable=bool(m.get("fix")),
                            end_line=m.get("endLine"),
                            end_column=m.get("endColumn")
                        ))
        except Exception:
            pass

        return diagnostics, duration_ms
