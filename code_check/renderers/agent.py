"""
Deterministic, machine-readable JSON renderer for AI coding agents and CI systems.
"""

import sys
from ..ir import Report

def render_agent_json(report: Report) -> None:
    """Print pure deterministic JSON representation of analysis report."""
    print(report.to_json(indent=2))
