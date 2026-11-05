"""
Oxlint static analysis adapter for JavaScript, TypeScript, and React correctness rules.
"""

import json
from pathlib import Path
from typing import List, Tuple, Optional
from .base import BaseAnalyzer, normalize_file_path
from ..ir import Diagnostic

class OxlintAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__("oxlint")

    @property
    def name(self) -> str:
        return "oxlint"

    @property
    def supported_languages(self) -> List[str]:
        return ["javascript", "typescript"]

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
        cmd = [self.executable_path, "-f", "json", "--react-plugin", "-D", "suspicious"]
        if fix:
            cmd.append("--fix")
        cmd.extend(str(f) for f in files)

        retcode, stdout, stderr, duration_ms = self._execute_process(cmd, run_cwd, timeout_sec)

        stdout = stdout.strip()
        if not stdout or not (stdout.startswith("{") or stdout.startswith("[")):
            return [], duration_ms

        diagnostics = []
        try:
            data = json.loads(stdout)
            # Format 1: Oxc native JSON schema { "diagnostics": [...] }
            if isinstance(data, dict) and "diagnostics" in data:
                for item in data.get("diagnostics", []):
                    rule = item.get("code") or "oxlint"
                    sev_raw = item.get("severity", "error")
                    severity = "error" if sev_raw.lower() == "error" else "warning"
                    msg = item.get("message", "")
                    if item.get("help"):
                        msg += f" ({item['help']})"

                    fpath = item.get("filename", "")
                    norm_file = normalize_file_path(fpath, cwd=run_cwd)
                    line, col = 1, 1
                    labels = item.get("labels", [])
                    if labels and "span" in labels[0]:
                        line = labels[0]["span"].get("line", 1)
                        col = labels[0]["span"].get("column", 1)

                    category = "bug"
                    if "react" in rule.lower() or "hooks" in rule.lower():
                        category = "bug"
                    elif "security" in rule.lower():
                        category = "security"
                    elif "perf" in rule.lower():
                        category = "performance"

                    diagnostics.append(Diagnostic(
                        severity=severity,
                        category=category,
                        file=norm_file,
                        line=line,
                        column=col,
                        rule=rule,
                        message=msg,
                        tool=self.name,
                        fixable=False,
                        help=item.get("help"),
                        url=item.get("url")
                    ))

            # Format 2: ESLint array format [ { "filePath": "...", "messages": [...] } ]
            elif isinstance(data, list):
                for file_entry in data:
                    fpath = file_entry.get("filePath", "")
                    norm_file = normalize_file_path(fpath, cwd=run_cwd)
                    for m in file_entry.get("messages", []):
                        rule = m.get("ruleId") or "oxlint"
                        sev_num = m.get("severity", 2)
                        severity = "error" if sev_num == 2 else "warning"

                        category = "bug" if "error" in severity else "style"
                        if "react" in rule.lower() or "hooks" in rule.lower():
                            category = "bug"
                        elif "security" in rule.lower():
                            category = "security"

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
