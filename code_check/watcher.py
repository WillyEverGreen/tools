"""
Persistent file watching daemon providing instant incremental feedback on file save.
Tracks filesystem change events and measures diagnostic latency.
"""

from __future__ import annotations
import os
import sys
import time
from pathlib import Path
from typing import Dict, Set, Optional, List, Tuple

from .ir import Report
from .runner import AnalysisRunner
from .detector import ProjectDetector, SUPPORTED_EXTENSIONS
from .renderers.terminal import render_terminal, bold, cyan, green, yellow, gray, red

class FileWatcher:
    """Monitors filesystem changes and triggers incremental static analysis."""

    def __init__(
        self,
        root: Path,
        runner: AnalysisRunner,
        debounce_ms: int = 250,
        deep: bool = False,
        security: bool = False,
        types: bool = False
    ):
        self.root = root.resolve()
        self.runner = runner
        self.debounce_sec = debounce_ms / 1000.0
        self.deep = deep
        self.security = security
        self.types = types
        self.detector = ProjectDetector(self.root)
        self.tracked_files: List[Path] = []
        self.mtimes: Dict[Path, int] = {}
        self.latency_samples: List[float] = []

    def _refresh_tracked_files(self) -> None:
        """Collect all relevant source files in the project."""
        self.tracked_files = self.detector.collect_files()

    def _scan_mtimes(self) -> Dict[Path, int]:
        """Collect current modification timestamps for all tracked source files."""
        current = {}
        for f in self.tracked_files:
            try:
                current[f] = f.stat().st_mtime_ns
            except OSError:
                pass
        return current

    def check_once(self) -> Optional[Tuple_Report_Latency]:
        """Check for changed files once, run incremental analysis if any changed, and return report & latency."""
        t_event = time.perf_counter()
        current_mtimes = self._scan_mtimes()

        changed_files: Set[Path] = set()
        for p, mtime in current_mtimes.items():
            if p not in self.mtimes or self.mtimes[p] != mtime:
                changed_files.add(p)

        if not changed_files:
            return None

        # Apply debounce
        if self.debounce_sec > 0:
            time.sleep(self.debounce_sec)
            current_mtimes = self._scan_mtimes()

        self.mtimes = current_mtimes

        # Re-analyze only changed files
        report = self.runner.run(
            list(changed_files),
            deep=self.deep,
            security=self.security,
            types=self.types
        )

        latency_ms = (time.perf_counter() - t_event) * 1000
        self.latency_samples.append(latency_ms)
        return report, list(changed_files), latency_ms

    def watch(self, max_iterations: Optional[int] = None) -> None:
        """Main persistent watch loop."""
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

        print(bold("\ncode-check watch daemon active"))
        print(gray(f"   Root:     {self.root}"))
        print(gray(f"   Debounce: {int(self.debounce_sec * 1000)}ms  ·  Press Ctrl+C to exit\n"))

        # Initial baseline scan
        self._refresh_tracked_files()
        initial_report = self.runner.run(
            self.tracked_files,
            deep=self.deep,
            security=self.security,
            types=self.types
        )
        self._print_banner("Initial Scan", initial_report)
        render_terminal(initial_report)

        self.mtimes = self._scan_mtimes()

        iterations = 0
        cycle_counter = 0

        try:
            while True:
                if max_iterations is not None and iterations >= max_iterations:
                    break

                time.sleep(0.05)  # 50ms fast poll
                cycle_counter += 1

                # Periodically re-discover newly added files every 20 cycles (~1 sec)
                if cycle_counter % 20 == 0:
                    self._refresh_tracked_files()

                result = self.check_once()
                if result:
                    iterations += 1
                    report, changed_files, latency_ms = result
                    t_stamp = time.strftime("%H:%M:%S")
                    f_names = ", ".join(f.name for f in changed_files)
                    tools_str = ", ".join(report.summary.tools_executed) or "fast-tier"

                    # Print structured watch event
                    print(bold(f"\n[{t_stamp}] File Change Detected: {cyan(f_names)}"))
                    print(gray(f"   Analyzers Executed: {tools_str}"))
                    print(gray(f"   Diagnostic Latency: {latency_ms:.1f}ms (event -> result)"))
                    print(gray(f"   Issue Summary:      {report.summary.errors} errors · {report.summary.warnings} warnings"))
                    print()
                    render_terminal(report)

        except KeyboardInterrupt:
            print("\nWatch daemon stopped cleanly.")

    def _print_banner(self, title: str, report: Report) -> None:
        status_icon = green("[PASS]") if report.summary.clean else yellow("[ISSUES]")
        print(bold(f"{status_icon} code-check  ·  {title}"))
        print(gray("─" * 60))

# Helper type alias
Tuple_Report_Latency = tuple
