"""
Command-line interface and entrypoint orchestration for code-check.
"""

import sys
import argparse
from pathlib import Path
from typing import List, Optional

from .ir import Report
from .config import Config
from .detector import ProjectDetector
from .runner import AnalysisRunner
from .fixer import AutoFixer
from .watcher import FileWatcher
from .doctor import run_doctor
from .renderers.terminal import render_terminal
from .renderers.agent import render_agent_json

# Exit Codes Protocol
EXIT_CLEAN = 0
EXIT_ISSUES = 1
EXIT_FAILURE = 2
EXIT_USAGE = 3

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="code-check",
        description="Local-First Multi-Language Static-Analysis Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  doctor                        Inspect installed tools and environment readiness

Exit Codes:
  0 = clean (no code issues)
  1 = issues detected (errors, or warnings with --strict)
  2 = tool/configuration execution failure
  3 = invalid CLI invocation

Examples:
  code-check                    # Fast analysis on current project
  code-check --changed          # Incremental analysis on Git-modified files only
  code-check --fix              # Auto-repair fixable issues and re-check
  code-check --deep             # Deep tier: includes Pyright and tsc type analysis
  code-check --security         # Security tier: Semgrep, Gitleaks, OSV-Scanner
  code-check --watch            # Persistent local daemon providing instant feedback on save
  code-check --agent            # Machine-readable JSON for AI coding agents & CI
  code-check doctor             # Print environment and analyzer availability report
"""
    )
    parser.add_argument("paths", nargs="*", default=["."], help="Files or directories to check (default: .) or 'doctor'")
    parser.add_argument("--changed", action="store_true", help="Analyze only git-modified, staged, and untracked files")
    parser.add_argument("--fix", action="store_true", help="Automatically fix safe issues, then re-check remaining issues")
    parser.add_argument("--watch", action="store_true", help="Start persistent file-watching daemon for instant feedback on save")
    parser.add_argument("--debounce", type=int, default=250, help="Watch mode debounce time in milliseconds (default: 250)")
    parser.add_argument("--deep", action="store_true", help="Enable deep static type analysis (Pyright for Python, tsc for TypeScript)")
    parser.add_argument("--types", action="store_true", help="Explicitly run type checkers (Pyright / tsc)")
    parser.add_argument("--security", action="store_true", help="Run local security vulnerability and secret scanning (Semgrep, Gitleaks, OSV-Scanner)")
    parser.add_argument("--agent", "--json", "--machine", dest="agent_mode", action="store_true", help="Output machine-readable unified JSON for AI coding agents & CI")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors (exit code 1 if warnings found)")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimize output to terminal")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print per-tool execution times and diagnostic details")
    parser.add_argument("--version", action="version", version="code-check 2.0.0")

    return parser

def run_cli(argv: Optional[List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # Intercept 'doctor' command
    if argv and argv[0] == "doctor":
        return run_doctor()

    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return EXIT_USAGE if e.code != 0 else EXIT_CLEAN

    # Also handle doctor if passed as positional argument without flags
    if args.paths == ["doctor"]:
        return run_doctor()

    root = Path.cwd()

    try:
        config = Config.load(root)
        runner = AnalysisRunner(root, config=config)

        # Watch Mode
        if args.watch:
            debounce = args.debounce if args.debounce != 250 else config.debounce_ms
            watcher = FileWatcher(
                root=root,
                runner=runner,
                debounce_ms=debounce,
                deep=args.deep or config.deep,
                security=args.security or config.security,
                types=args.types
            )
            watcher.watch()
            return EXIT_CLEAN

        # Collect Files
        detector = ProjectDetector(root, custom_excludes=config.ignored_paths)
        target_paths = [Path(p) for p in args.paths if p != "."]
        target_paths = target_paths if target_paths else [root]

        files = detector.collect_files(paths=target_paths, changed_only=args.changed)

        if not files:
            if args.agent_mode:
                summary = runner.run([]).summary
                render_agent_json(Report(summary=summary, issues=[]))
            else:
                if not args.quiet:
                    if args.changed:
                        print("No modified, staged, or untracked source files found via Git.")
                    else:
                        print("No supported Python or JS/TS source files found to check.")
            return EXIT_CLEAN

        fixed_count = 0

        # Auto-Fix Mode
        if args.fix:
            fixer = AutoFixer(runner)
            report, fixed_count = fixer.fix_and_verify(
                files,
                deep=args.deep or config.deep,
                security=args.security or config.security,
                types=args.types
            )
        else:
            # Standard, Deep, or Security Run
            report = runner.run(
                files,
                deep=args.deep or config.deep,
                security=args.security or config.security,
                types=args.types,
                fix=False
            )

        # Render Output
        if args.agent_mode:
            render_agent_json(report)
        else:
            render_terminal(report, fixed_count=fixed_count, verbose=args.verbose, quiet=args.quiet)

        # Exit Code Protocol
        is_strict = args.strict or config.strict
        if report.summary.errors > 0 or report.summary.security_issues > 0:
            return EXIT_ISSUES
        if is_strict and report.summary.warnings > 0:
            return EXIT_ISSUES

        return EXIT_CLEAN

    except Exception as err:
        sys.stderr.write(f"code-check error: {err}\n")
        return EXIT_FAILURE

def main():
    sys.exit(run_cli())

if __name__ == "__main__":
    main()
