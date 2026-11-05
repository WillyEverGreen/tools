"""
Renderers for human terminal presentation and machine agent JSON.
"""

from .terminal import render_terminal
from .agent import render_agent_json

__all__ = ["render_terminal", "render_agent_json"]
