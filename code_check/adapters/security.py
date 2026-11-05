"""
Security, secrets, and dependency vulnerability analyzer adapters.
Provides robust adapters for Semgrep, Gitleaks, and OSV-Scanner with graceful fallback.
"""

import json
from pathlib import Path
from typing import List, Tuple, Optional
from .base import BaseAnalyzer, normalize_file_path
from ..ir import Diagnostic

class SemgrepAnalyzer(BaseAnalyzer):
    """Semgrep deep security and custom semantic pattern analyzer."""

    def __init__(self):
        super().__init__("semgrep")

    @property
    def name(self) -> str:
        return "semgrep"

    @property
    def supported_languages(self) -> List[str]:
        return ["python", "javascript", "typescript"]

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
        cmd = [self.executable_path, "scan", "--json", "--quiet", "--config", "auto"]
        retcode, stdout, stderr, duration_ms = self._execute_process(cmd, run_cwd, timeout_sec)

        diagnostics = []
        try:
            data = json.loads(stdout)
            for res in data.get("results", []):
                rule_id = res.get("check_id", "security-issue")
                msg = res.get("extra", {}).get("message", "Security vulnerability detected")
                path = res.get("path", "")
                norm_file = normalize_file_path(path, cwd=run_cwd)
                start = res.get("start", {})

                diagnostics.append(Diagnostic(
                    severity="security",
                    category="security",
                    file=norm_file,
                    line=start.get("line", 1),
                    column=start.get("col", 1),
                    rule=rule_id,
                    message=msg,
                    tool=self.name,
                    fixable=False
                ))
        except Exception:
            pass

        return diagnostics, duration_ms


class GitleaksAnalyzer(BaseAnalyzer):
    """Gitleaks secrets and credentials detector."""

    def __init__(self):
        super().__init__("gitleaks")

    @property
    def name(self) -> str:
        return "gitleaks"

    @property
    def supported_languages(self) -> List[str]:
        return ["*"]

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
        cmd = [self.executable_path, "detect", "--no-git", "-v", "--report-format", "json"]
        retcode, stdout, stderr, duration_ms = self._execute_process(cmd, run_cwd, timeout_sec)

        diagnostics = []
        try:
            data = json.loads(stdout)
            for leak in data:
                rule_id = leak.get("RuleID", "secret-detected")
                desc = leak.get("Description", "Secret or credential detected in source")
                path = leak.get("File", "")
                norm_file = normalize_file_path(path, cwd=run_cwd)
                line = leak.get("StartLine", 1)

                diagnostics.append(Diagnostic(
                    severity="security",
                    category="security",
                    file=norm_file,
                    line=line,
                    column=1,
                    rule=rule_id,
                    message=desc,
                    tool=self.name,
                    fixable=False
                ))
        except Exception:
            pass

        return diagnostics, duration_ms


class OsvScannerAnalyzer(BaseAnalyzer):
    """OSV-Scanner open-source dependency vulnerability scanner."""

    def __init__(self):
        super().__init__("osv-scanner")

    @property
    def name(self) -> str:
        return "osv-scanner"

    @property
    def supported_languages(self) -> List[str]:
        return ["*"]

    def run(
        self,
        files: List[Path],
        fix: bool = False,
        cwd: Optional[Path] = None,
        timeout_sec: float = 45.0
    ) -> Tuple[List[Diagnostic], float]:
        if not self.is_available:
            return [], 0.0

        run_cwd = cwd or Path.cwd()
        cmd = [self.executable_path, "--json", "-r", "."]
        retcode, stdout, stderr, duration_ms = self._execute_process(cmd, run_cwd, timeout_sec)

        diagnostics = []
        try:
            data = json.loads(stdout)
            for result in data.get("results", []):
                source = result.get("source", {}).get("path", "package-lock")
                norm_file = normalize_file_path(source, cwd=run_cwd)
                for pkg in result.get("packages", []):
                    pkg_info = pkg.get("package", {})
                    pkg_name = pkg_info.get("name", "dependency")
                    pkg_ver = pkg_info.get("version", "")
                    for vuln in pkg.get("vulnerabilities", []):
                        vuln_id = vuln.get("id", "CVE")
                        summary = vuln.get("summary") or f"Vulnerability in {pkg_name} {pkg_ver}"
                        diagnostics.append(Diagnostic(
                            severity="security",
                            category="dependency",
                            file=norm_file,
                            line=1,
                            column=1,
                            rule=vuln_id,
                            message=summary,
                            tool=self.name,
                            fixable=False
                        ))
        except Exception:
            pass

        return diagnostics, duration_ms

# Legacy alias
SecurityAnalyzer = SemgrepAnalyzer
