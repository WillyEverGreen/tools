"""
Doctor environment diagnostic module for code-check.
Inspects system PATH and C:\\tools to verify installed static analysis engines.
"""

import sys
import re
from typing import Dict, Tuple, Optional
from .adapters import (
    RuffAnalyzer,
    OxlintAnalyzer,
    AstGrepAnalyzer,
    PyrightAnalyzer,
    TscAnalyzer,
    SemgrepAnalyzer,
    GitleaksAnalyzer,
    OsvScannerAnalyzer
)
from .renderers.terminal import green, yellow, bold, gray

def extract_version(raw: Optional[str]) -> Optional[str]:
    """Extract clean semver version string from raw tool output."""
    if not raw:
        return None
    m = re.search(r'(\d+\.\d+(?:\.\d+)?(?:-[a-zA-Z0-9.]+)?|\d+\.\d+)', raw)
    if m:
        return m.group(1)
    return raw.strip()

def check_environment() -> Dict[str, Tuple[bool, str]]:
    """Inspect availability and versions of all supported analyzers."""
    results = {}

    # 1. Python runtime
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    results["Python"] = (True, py_ver)

    # 2. Fast Tier
    ruff = RuffAnalyzer()
    results["Ruff"] = (ruff.is_available, extract_version(ruff.get_version()) or "available" if ruff.is_available else "unavailable")

    oxlint = OxlintAnalyzer()
    results["Oxlint"] = (oxlint.is_available, extract_version(oxlint.get_version()) or "available" if oxlint.is_available else "unavailable")

    sg = AstGrepAnalyzer()
    results["ast-grep"] = (sg.is_available, extract_version(sg.get_version()) or "available" if sg.is_available else "unavailable")

    # 3. Deep / Types Tier
    pyright = PyrightAnalyzer()
    results["Pyright"] = (pyright.is_available, extract_version(pyright.get_version()) or "available" if pyright.is_available else "unavailable")

    tsc = TscAnalyzer()
    results["TypeScript"] = (tsc.is_available, extract_version(tsc.get_version()) or "available" if tsc.is_available else "unavailable")

    # 4. Security Tier
    semgrep = SemgrepAnalyzer()
    results["Semgrep"] = (semgrep.is_available, extract_version(semgrep.get_version()) or "available" if semgrep.is_available else "unavailable")

    gitleaks = GitleaksAnalyzer()
    results["Gitleaks"] = (gitleaks.is_available, extract_version(gitleaks.get_version()) or "available" if gitleaks.is_available else "unavailable")

    osv = OsvScannerAnalyzer()
    results["OSV-Scanner"] = (osv.is_available, extract_version(osv.get_version()) or "available" if osv.is_available else "unavailable")

    return results

def run_doctor() -> int:
    """Print clean environment diagnostic report to terminal."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print(bold("\ncode-check environment\n"))

    # Choose marks based on terminal capability
    can_unicode = True
    try:
        "✓○".encode(sys.stdout.encoding or "utf-8")
    except Exception:
        can_unicode = False

    mark_ok = "✓" if can_unicode else "[+]"
    mark_no = "○" if can_unicode else "[-]"

    env_data = check_environment()
    for tool_name, (avail, ver) in env_data.items():
        if avail:
            mark = green(mark_ok)
            print(f"  {mark} {tool_name:<14} {ver}")
        else:
            mark = gray(mark_no)
            print(f"  {mark} {tool_name:<14} {gray(ver)}")

    print()
    return 0
