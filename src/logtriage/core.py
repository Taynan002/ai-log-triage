from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import re
from typing import Iterable


LEVEL_RE = re.compile(r"\b(TRACE|DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL|FATAL)\b", re.IGNORECASE)
TIMESTAMP_RE = re.compile(
    r"^\s*(?P<timestamp>\d{4}-\d{2}-\d{2}[T ][0-9:.+-]+(?:Z)?)\s*"
)

UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
HEX_RE = re.compile(r"\b0x[0-9a-f]+\b", re.IGNORECASE)
NUMBER_RE = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?(?![A-Za-z])")
WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class LogEntry:
    level: str
    message: str
    timestamp: str | None = None


def _canonical_level(level: str) -> str:
    value = level.upper()
    if value == "WARN":
        return "WARNING"
    if value == "FATAL":
        return "CRITICAL"
    return value


def parse_line(line: str) -> LogEntry | None:
    """Parse a log line using tolerant level/timestamp detection."""
    raw = line.strip()
    if not raw:
        return None

    timestamp = None
    timestamp_match = TIMESTAMP_RE.match(raw)
    if timestamp_match:
        timestamp = timestamp_match.group("timestamp")
        raw = raw[timestamp_match.end():].lstrip(" -|[]")

    level_match = LEVEL_RE.search(raw)
    if not level_match:
        return None

    level = _canonical_level(level_match.group(1))
    message = raw[level_match.end():].lstrip(" :|-[]")
    if not message:
        message = "(no message)"

    return LogEntry(level=level, message=message, timestamp=timestamp)


def normalize_message(message: str) -> str:
    """Replace volatile identifiers so repeated failures group together."""
    normalized = UUID_RE.sub("<uuid>", message)
    normalized = IP_RE.sub("<ip>", normalized)
    normalized = HEX_RE.sub("<hex>", normalized)
    normalized = NUMBER_RE.sub("<num>", normalized)
    normalized = WHITESPACE_RE.sub(" ", normalized).strip()
    return normalized


def analyze_lines(lines: Iterable[str], top: int = 10) -> dict:
    """Return deterministic aggregate diagnostics for an iterable of log lines."""
    if top < 1:
        raise ValueError("top must be >= 1")

    total_lines = 0
    entries: list[LogEntry] = []
    level_counts: Counter[str] = Counter()
    signature_counts: Counter[tuple[str, str]] = Counter()

    for line in lines:
        total_lines += 1
        entry = parse_line(line)
        if entry is None:
            continue

        entries.append(entry)
        level_counts[entry.level] += 1

        if entry.level in {"WARNING", "ERROR", "CRITICAL"}:
            signature_counts[(entry.level, normalize_message(entry.message))] += 1

    top_signatures = [
        {"level": level, "signature": signature, "count": count}
        for (level, signature), count in signature_counts.most_common(top)
    ]

    return {
        "total_lines": total_lines,
        "parsed_entries": len(entries),
        "unparsed_lines": total_lines - len(entries),
        "levels": dict(sorted(level_counts.items())),
        "top_signatures": top_signatures,
    }


def render_text(report: dict) -> str:
    """Render a compact human-readable report."""
    lines = [
        "Log triage report",
        "=================",
        f"Total lines: {report['total_lines']}",
        f"Parsed entries: {report['parsed_entries']}",
        f"Unparsed lines: {report['unparsed_lines']}",
        "",
        "Levels:",
    ]

    if report["levels"]:
        for level, count in report["levels"].items():
            lines.append(f"  {level}: {count}")
    else:
        lines.append("  (none)")

    lines.extend(["", "Top warning/error signatures:"])
    if report["top_signatures"]:
        for item in report["top_signatures"]:
            lines.append(
                f"  [{item['level']}] x{item['count']} {item['signature']}"
            )
    else:
        lines.append("  (none)")

    return "\n".join(lines)
