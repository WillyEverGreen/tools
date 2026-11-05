"""
ast-grep (sg) adapter for custom structural AST rules and pattern matching.
"""

import json
from pathlib import Path
from typing import List, Tuple, Optional
from .base import BaseAnalyzer, normalize_file_path
from ..ir import Diagnostic

class AstGrepAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__("sg")

    @property
    def name(self) -> str:
        return "ast-grep"

    @property
    def supported_languages(self) -> List[str]:
        return ["python", "javascript", "typescript", "rust", "go", "java", "c", "cpp"]

    def run(
        self,
        files: List[Path],
        fix: bool = False,
        cwd: Optional[Path] = None,
        timeout_sec: float = 30.0
    ) -> Tuple[List[Diagnostic], float]:
        if not self.is_available:
            return [], 0.0

        run_cwd = cwd or Path.cwd()
        # Look for custom rules in cwd or built-in rules directory
        has_config = (run_cwd / "sgconfig.yml").exists()
        rules_candidates = [
            run_cwd / "rules" / "ast-grep",
            Path(__file__).resolve().parent.parent.parent / "rules" / "ast-grep",
            Path(r"C:\tools\rules\ast-grep")
        ]
        rules_dir = next((r for r in rules_candidates if r.exists()), None)

        if not has_config and not rules_dir:
            return [], 0.0

        cmd = [self.executable_path, "scan", "--json=compact"]
        if not has_config and rules_dir:
            cmd.extend(["--rule", str(rules_dir)])

        retcode, stdout, stderr, duration_ms = self._execute_process(cmd, run_cwd, timeout_sec)

        stdout = stdout.strip()
        if not stdout or not stdout.startswith("["):
            return [], duration_ms

        allowed_files = {f.resolve() for f in files} if files else None

        diagnostics = []
        try:
            data = json.loads(stdout)
            for item in data:
                fpath = item.get("file", "")
                norm_file = normalize_file_path(fpath, cwd=run_cwd)

                if allowed_files:
                    resolved = (run_cwd / fpath).resolve()
                    if resolved not in allowed_files:
                        continue

                rng = item.get("range", {}).get("start", {})
                rule_id = item.get("ruleId", "structural-rule")
                msg = item.get("message") or "Structural pattern violation"

                diagnostics.append(Diagnostic(
                    severity=item.get("severity", "warning").lower(),
                    category="architecture",
                    file=norm_file,
                    line=rng.get("line", 0) + 1,
                    column=rng.get("column", 0) + 1,
                    rule=rule_id,
                    message=msg,
                    tool=self.name,
                    fixable=False
                ))
        except Exception:
            pass

        return diagnostics, duration_ms
