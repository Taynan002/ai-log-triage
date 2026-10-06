from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import analyze_lines, render_text
from .llm import LLMConfigurationError, summarize_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="logtriage",
        description="Group recurring warnings and errors from application logs.",
    )
    parser.add_argument("logfile", type=Path, help="Path to a UTF-8 log file")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        dest="output_format",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Maximum number of recurring signatures to show (default: 10)",
    )
    parser.add_argument(
        "--ai-summary",
        action="store_true",
        help="Add an optional summary using an OpenAI-compatible endpoint",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.top < 1:
        raise SystemExit("--top must be >= 1")

    try:
        with args.logfile.open("r", encoding="utf-8", errors="replace") as handle:
            report = analyze_lines(handle, top=args.top)
    except OSError as exc:
        raise SystemExit(f"Could not read {args.logfile}: {exc}") from exc

    if args.ai_summary:
        try:
            report["ai_summary"] = summarize_report(report)
        except LLMConfigurationError as exc:
            raise SystemExit(str(exc)) from exc
        except RuntimeError as exc:
            raise SystemExit(f"AI summary unavailable: {exc}") from exc

    if args.output_format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(render_text(report))
        if "ai_summary" in report:
            print("\nAI-assisted summary")
            print("===================")
            print(report["ai_summary"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
