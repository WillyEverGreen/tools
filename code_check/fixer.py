"""
Safe auto-fix loop: executes fixable rules then re-analyzes to report remaining issues.
"""

from pathlib import Path
from typing import List, Tuple
from .ir import Report
from .runner import AnalysisRunner

class AutoFixer:
    """Coordinates safe automatic fixing followed by clean verification re-scan."""

    def __init__(self, runner: AnalysisRunner):
        self.runner = runner

    def fix_and_verify(
        self,
        files: List[Path],
        deep: bool = False,
        security: bool = False,
        types: bool = False
    ) -> Tuple[Report, int]:
        """
        1. Run initial analysis to count initial fixable issues.
        2. Apply safe fixes using Ruff and Oxlint.
        3. Re-run analysis without fix flag to accurately report remaining issues.
        Returns: (final_report, count_of_fixed_issues)
        """
        # Step 1: Initial scan
        initial_report = self.runner.run(files, deep=deep, security=security, types=types, fix=False)
        initial_fixable = initial_report.summary.fixable_issues

        if initial_fixable == 0:
            return initial_report, 0

        # Step 2: Apply fixes
        self.runner.run(files, deep=deep, security=security, types=types, fix=True)

        # Step 3: Re-verify remaining issues
        final_report = self.runner.run(files, deep=deep, security=security, types=types, fix=False)
        remaining_fixable = final_report.summary.fixable_issues
        actually_fixed = max(0, initial_fixable - remaining_fixable)

        return final_report, actually_fixed
