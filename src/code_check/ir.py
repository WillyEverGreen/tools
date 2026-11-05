"""
Unified Diagnostic Intermediate Representation (IR).
Provides immutable, stable data models normalizing all analyzer outputs.
"""

import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any

VALID_SEVERITIES = {"error", "warning", "security", "info"}
VALID_CATEGORIES = {
    "syntax", "bug", "style", "type", "security",
    "dependency", "architecture", "performance", "tooling", "unknown"
}

@dataclass(frozen=True)
class Diagnostic:
    """Standardized issue record independent of underlying analyzer."""
    severity: str        # "error" | "warning" | "security" | "info"
    category: str        # "syntax" | "bug" | "style" | "type" | "security" | ...
    file: str            # Normalized path
    line: int            # 1-indexed
    column: int          # 1-indexed
    rule: str            # Original tool rule identifier
    message: str         # Human-readable explanation
    tool: str            # "ruff" | "oxlint" | "pyright" | "tsc" | "ast-grep" | "semgrep" | ...
    fixable: bool = False
    end_line: Optional[int] = None
    end_column: Optional[int] = None
    fix: Optional[str] = None
    help: Optional[str] = None
    url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert diagnostic to clean dictionary omitting null optional metadata."""
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}

@dataclass
class DiagnosticSummary:
    """Aggregated analysis telemetry and counts."""
    total_issues: int = 0
    errors: int = 0
    warnings: int = 0
    security_issues: int = 0
    fixable_issues: int = 0
    files_checked: int = 0
    duration_ms: float = 0.0
    tool_timings_ms: Dict[str, float] = field(default_factory=dict)
    tools_executed: List[str] = field(default_factory=list)
    tools_available: List[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        return "passed" if self.errors == 0 and self.security_issues == 0 else "failed"

    @property
    def clean(self) -> bool:
        return self.total_issues == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "clean": self.clean,
            "total_issues": self.total_issues,
            "errors": self.errors,
            "warnings": self.warnings,
            "security": self.security_issues,
            "security_issues": self.security_issues,
            "fixable": self.fixable_issues,
            "fixable_issues": self.fixable_issues,
            "files_checked": self.files_checked,
            "tools_run": self.tools_executed,
            "tools_executed": self.tools_executed,
            "tools_available": self.tools_available,
            "duration_ms": round(self.duration_ms, 2),
            "tool_timings_ms": {k: round(v, 2) for k, v in self.tool_timings_ms.items()}
        }

@dataclass
class Report:
    """Full analysis report combining summary and unified diagnostics list."""
    summary: DiagnosticSummary
    issues: List[Diagnostic] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.summary.status,
            "clean": self.summary.clean,
            "summary": self.summary.to_dict(),
            "issues": [d.to_dict() for d in self.issues]
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False)
