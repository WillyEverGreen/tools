"""
Analysis runner scheduling and coordinating heterogeneous analyzer adapters.
"""

import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Set, Optional, Tuple

from .ir import Diagnostic, DiagnosticSummary, Report
from .config import Config
from .detector import ProjectDetector
from .adapters import (
    BaseAnalyzer,
    RuffAnalyzer,
    OxlintAnalyzer,
    EslintAnalyzer,
    PyrightAnalyzer,
    TscAnalyzer,
    AstGrepAnalyzer,
    SemgrepAnalyzer,
    GitleaksAnalyzer,
    OsvScannerAnalyzer
)

class AnalysisRunner:
    """Orchestrates multi-language static analysis across configured adapters."""

    def __init__(self, root: Path, config: Optional[Config] = None):
        self.root = root.resolve()
        self.config = config or Config.load(self.root)
        self.detector = ProjectDetector(self.root, custom_excludes=self.config.ignored_paths)

        # Initialize all known adapters
        self.analyzers: Dict[str, BaseAnalyzer] = {
            "ruff": RuffAnalyzer(),
            "oxlint": OxlintAnalyzer(),
            "eslint": EslintAnalyzer(),
            "pyright": PyrightAnalyzer(),
            "tsc": TscAnalyzer(),
            "ast-grep": AstGrepAnalyzer(),
            "semgrep": SemgrepAnalyzer(),
            "gitleaks": GitleaksAnalyzer(),
            "osv-scanner": OsvScannerAnalyzer()
        }

    def get_available_tools(self) -> List[str]:
        """Return list of analyzer names whose binaries are installed on system."""
        return [name for name, a in self.analyzers.items() if a.is_available]

    def run(
        self,
        files: List[Path],
        deep: bool = False,
        security: bool = False,
        types: bool = False,
        fix: bool = False
    ) -> Report:
        """Execute analyzers concurrently and return normalized unified Report."""
        if not files:
            summary = DiagnosticSummary(
                tools_available=self.get_available_tools()
            )
            return Report(summary=summary, issues=[])

        # Filter out ignored paths
        if self.config.ignored_paths:
            filtered = []
            for f in files:
                rel = str(f.relative_to(self.root) if f.is_relative_to(self.root) else f)
                if not any(ign in rel for ign in self.config.ignored_paths):
                    filtered.append(f)
            files = filtered

        lang_map = self.detector.partition_by_language(files)
        has_python = len(lang_map["python"]) > 0
        has_js_ts = len(lang_map.get("all_js_ts", [])) > 0 or len(lang_map["javascript"]) > 0 or len(lang_map["typescript"]) > 0
        has_ts = len(lang_map["typescript"]) > 0

        # Determine which analyzers to run
        tasks = []  # List of (analyzer, target_files, is_fix)
        enabled = set(self.config.enabled_analyzers)

        # 1. Fast Tier
        if "ruff" in enabled and has_python:
            tasks.append((self.analyzers["ruff"], lang_map["python"], fix))

        if "oxlint" in enabled and has_js_ts:
            all_js = lang_map.get("all_js_ts") or list(set(lang_map["javascript"] + lang_map["typescript"]))
            tasks.append((self.analyzers["oxlint"], all_js, fix))

        # ast-grep: structural rules (only if rules exist)
        if "ast-grep" in enabled:
            tasks.append((self.analyzers["ast-grep"], files, False))

        # 2. Deep / Types Tier
        run_type_checks = deep or types or self.config.deep
        if run_type_checks:
            if "pyright" in enabled and has_python:
                tasks.append((self.analyzers["pyright"], lang_map["python"], False))
            if "tsc" in enabled and has_ts:
                tasks.append((self.analyzers["tsc"], lang_map["typescript"], False))
            if "eslint" in enabled and has_js_ts:
                all_js = lang_map.get("all_js_ts") or list(set(lang_map["javascript"] + lang_map["typescript"]))
                tasks.append((self.analyzers["eslint"], all_js, fix))

        # 3. Security Tier
        run_security = security or self.config.security
        if run_security:
            for sec_name in ["semgrep", "gitleaks", "osv-scanner"]:
                if sec_name in enabled and self.analyzers[sec_name].is_available:
                    tasks.append((self.analyzers[sec_name], files, False))

        # Execute analyzers in parallel
        diagnostics: List[Diagnostic] = []
        tool_timings: Dict[str, float] = {}
        executed_tools: List[str] = []

        t_start = time.perf_counter()

        def execute_task(task_spec):
            analyzer, target_files, do_fix = task_spec
            if not analyzer.is_available:
                return analyzer.name, [], 0.0
            try:
                diags, dur_ms = analyzer.run(target_files, fix=do_fix, cwd=self.root)
                return analyzer.name, diags, dur_ms
            except Exception as exc:
                import sys
                sys.stderr.write(f"Warning: analyzer {analyzer.name} encountered an error: {exc}\n")
                return analyzer.name, [], 0.0

        with ThreadPoolExecutor(max_workers=min(4, max(1, len(tasks)))) as executor:
            results = executor.map(execute_task, tasks)
            for tool_name, diags, dur_ms in results:
                if dur_ms > 0:
                    tool_timings[tool_name] = dur_ms
                    executed_tools.append(tool_name)
                    diagnostics.extend(diags)

        total_duration_ms = (time.perf_counter() - t_start) * 1000

        # Filter out disabled rules
        if self.config.disabled_rules:
            diagnostics = [
                d for d in diagnostics
                if d.rule not in self.config.disabled_rules
            ]

        # Sort diagnostics: errors first, then warnings, then file, line, col
        sev_rank = {"error": 0, "security": 1, "warning": 2, "info": 3}
        diagnostics.sort(key=lambda d: (sev_rank.get(d.severity, 4), d.file, d.line, d.column))

        # Apply max issues limit if configured
        if self.config.max_issues and len(diagnostics) > self.config.max_issues:
            diagnostics = diagnostics[:self.config.max_issues]

        # Compute summary
        error_cnt = sum(1 for d in diagnostics if d.severity == "error")
        warn_cnt = sum(1 for d in diagnostics if d.severity == "warning")
        sec_cnt = sum(1 for d in diagnostics if d.severity == "security")
        fixable_cnt = sum(1 for d in diagnostics if d.fixable)

        summary = DiagnosticSummary(
            total_issues=len(diagnostics),
            errors=error_cnt,
            warnings=warn_cnt,
            security_issues=sec_cnt,
            fixable_issues=fixable_cnt,
            files_checked=len(files),
            duration_ms=total_duration_ms,
            tool_timings_ms=tool_timings,
            tools_executed=executed_tools,
            tools_available=self.get_available_tools()
        )

        return Report(summary=summary, issues=diagnostics)
