from __future__ import annotations

import argparse
from pathlib import Path

from .analyzer import DemandAnalyzer
from .archiver import archive_report
from .collector import dedupe_comments, load_comments
from .llm_analyzer import LLMAnalyzer
from .task_router import write_agent_tasks


def run_pipeline(
    input_path: str | Path,
    out_dir: str | Path,
    platform: str = "unknown",
    analyzer_mode: str = "rules",
) -> dict[str, Path]:
    comments = dedupe_comments(load_comments(input_path, platform=platform))
    analyzer = LLMAnalyzer() if analyzer_mode == "llm" else DemandAnalyzer()
    report = analyzer.analyze(comments)
    paths = archive_report(report, out_dir)
    paths.update(write_agent_tasks(report, out_dir))
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze social comments and dispatch agent tasks")
    parser.add_argument("--input", required=True, help="Path to exported comments: .jsonl/.json/.csv")
    parser.add_argument("--out", default="out/latest", help="Output directory")
    parser.add_argument("--platform", default="unknown", help="Source platform name")
    parser.add_argument(
        "--analyzer",
        choices=("rules", "llm"),
        default="rules",
        help="Analyzer mode. llm uses OpenAI-compatible env vars and falls back to rules.",
    )
    args = parser.parse_args()
    paths = run_pipeline(args.input, args.out, platform=args.platform, analyzer_mode=args.analyzer)
    print("完成：")
    for name, path in paths.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
