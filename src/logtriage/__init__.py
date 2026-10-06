"""Small, deterministic building blocks for application log triage."""

from .core import analyze_lines, normalize_message, parse_line

__all__ = ["analyze_lines", "normalize_message", "parse_line"]
__version__ = "0.1.0"
