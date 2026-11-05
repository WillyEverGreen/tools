"""
Human-friendly ANSI terminal renderer.
"""

import sys
import os
from pathlib import Path
from typing import List, Optional
from ..ir import Report, Diagnostic

USE_COLOR = sys.stdout.isatty() or os.environ.get("FORCE_COLOR") == "1"

def c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text

def bold(text: str) -> str: return c(text, "1")
def red(text: str) -> str: return c(text, "31")
def green(text: str) -> str: return c(text, "32")
def yellow(text: str) -> str: return c(text, "33")
def blue(text: str) -> str: return c(text, "34")
def magenta(text: str) -> str: return c(text, "35")
def cyan(text: str) -> str: return c(text, "36")
def gray(text: str) -> str: return c(text, "90")

def render_terminal(report: Report, fixed_count: int = 0, verbose: bool = False, quiet: bool = False) -> None:
    """Print clean, standardized, human-readable terminal output."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    summary = report.summary
    cwd = Path.cwd()

    if report.summary.clean:
        dur = summary.duration_ms
        fc = summary.files_checked
        tools = ", ".join(summary.tools_executed) if summary.tools_executed else "analyzers"
        fixed_msg = f" ({green(f'{fixed_count} fixed')})" if fixed_count > 0 else ""
        print(f"\n{green('PASS')} Checked {bold(str(fc))} files in {bold(f'{dur:.1f}ms')} ({tools}) — {green('0 issues found')}{fixed_msg}.\n")
        return

    print()
    for d in report.issues:
        if d.severity == "error":
            sev_badge = bold(red("ERROR   "))
        elif d.severity == "security":
            sev_badge = bold(magenta("SECURITY"))
        elif d.severity == "warning":
            sev_badge = bold(yellow("WARNING "))
        else:
            sev_badge = bold(cyan("INFO    "))

        rel_path = d.file
        try:
            rel_path = str(Path(d.file).relative_to(cwd))
        except Exception:
            pass

        loc_str = f"{rel_path}:{d.line}:{d.column}"
        tool_tag = gray(f"[{d.tool.capitalize()}: {d.rule}]")
        fix_tag = green(" (fixable)") if d.fixable else ""

        print(f"{sev_badge} {bold(loc_str)}")
        print(f"         {d.message}")
        print(f"         {tool_tag}{fix_tag}\n")

    # Summary footer bar
    fc = summary.files_checked
    dur = summary.duration_ms
    err_cnt = summary.errors
    warn_cnt = summary.warnings
    sec_cnt = summary.security_issues
    fix_cnt = summary.fixable_issues
    tools_str = ", ".join(summary.tools_executed)

    parts = []
    if err_cnt: parts.append(red(f"{err_cnt} error{'s' if err_cnt != 1 else ''}"))
    if sec_cnt: parts.append(magenta(f"{sec_cnt} security issue{'s' if sec_cnt != 1 else ''}"))
    if warn_cnt: parts.append(yellow(f"{warn_cnt} warning{'s' if warn_cnt != 1 else ''}"))

    status_str = ", ".join(parts) if parts else green("clean")
    fix_info = f" ({green(f'{fix_cnt} fixable with --fix')})" if fix_cnt else ""
    if fixed_count > 0:
        fix_info = f" ({green(f'{fixed_count} auto-fixed')})"

    print(bold(f"Checked {fc} files in {dur:.1f}ms ({tools_str}) — {status_str}{fix_info}"))

    if verbose and summary.tool_timings_ms:
        print(gray("\nTool execution latencies:"))
        for tname, tms in summary.tool_timings_ms.items():
            print(f"  • {tname:<10}: {tms:.1f} ms")

    print()
