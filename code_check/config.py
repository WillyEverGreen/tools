"""
Configuration loader supporting .code-check.toml and zero-config defaults.
"""

import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any

try:
    import tomllib
except ImportError:
    tomllib = None  # type: ignore

@dataclass
class Config:
    """Project-level configuration settings."""
    enabled_analyzers: List[str] = field(default_factory=lambda: ["ruff", "oxlint", "ast-grep", "pyright", "tsc", "eslint"])
    disabled_rules: Set[str] = field(default_factory=set)
    ignored_paths: Set[str] = field(default_factory=set)
    debounce_ms: int = 200
    deep: bool = False
    security: bool = False
    strict: bool = False
    max_issues: int = 100

    @classmethod
    def load(cls, root: Path) -> "Config":
        """Load configuration from .code-check.toml, pyproject.toml, or use defaults."""
        config = cls()

        # 1. Check .code-check.toml
        cfg_file = root / ".code-check.toml"
        if cfg_file.exists() and tomllib:
            try:
                with open(cfg_file, "rb") as f:
                    data = tomllib.load(f)
                config._apply_dict(data)
                return config
            except Exception:
                pass

        # 2. Check pyproject.toml [tool.code-check]
        pyproj = root / "pyproject.toml"
        if pyproj.exists() and tomllib:
            try:
                with open(pyproj, "rb") as f:
                    data = tomllib.load(f)
                tool_data = data.get("tool", {}).get("code-check", {})
                if tool_data:
                    config._apply_dict(tool_data)
                    return config
            except Exception:
                pass

        return config

    def _apply_dict(self, data: Dict[str, Any]) -> None:
        """Apply parsed dictionary settings to configuration."""
        if "enabled_analyzers" in data:
            self.enabled_analyzers = list(data["enabled_analyzers"])
        if "disabled_rules" in data:
            self.disabled_rules = set(data["disabled_rules"])
        if "ignored_paths" in data:
            self.ignored_paths = set(data["ignored_paths"])
        if "debounce_ms" in data:
            self.debounce_ms = int(data["debounce_ms"])
        if "deep" in data:
            self.deep = bool(data["deep"])
        if "security" in data:
            self.security = bool(data["security"])
        if "strict" in data:
            self.strict = bool(data["strict"])
        if "max_issues" in data:
            self.max_issues = int(data["max_issues"])
