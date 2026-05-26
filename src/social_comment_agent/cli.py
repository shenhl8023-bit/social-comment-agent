from __future__ import annotations

import argparse
from pathlib import Path

from .analyzer import DemandAnalyzer
from .archiver import archive_report
from .collector import dedupe_comments, load_comments
from .llm_analyzer import LLMAnalyzer
from .platform_templates import get_platform_template
from .task_router import write_agent_tasks
from .kanban import dispatch_kanban_tasks, write_kanban_dry_run


def run_pipeline(
    input_path: str | Path,
    out_dir: str | Path,
    platform: str = "unknown",
    platform_template: str | None = None,
    analyzer_mode: str = "rules",
    dry_run_kanban: bool = False,
    dispatch_kanban: bool = False,
    kanban_workspace: str = "scratch",
    kanban_tenant: str | None = None,
) -> dict[str, Path]:
    template = get_platform_template(platform_template)
    effective_platform = template.default_platform if template and platform == "unknown" else platform
    comments = dedupe_comments(load_comments(input_path, platform=effective_platform))
    analyzer = LLMAnalyzer() if analyzer_mode == "llm" else DemandAnalyzer()
    report = analyzer.analyze(comments)
    paths = archive_report(report, out_dir)
    paths.update(write_agent_tasks(report, out_dir))
    if dry_run_kanban or dispatch_kanban:
        paths.update({
            f"kanban_dry_run_{key}": value
            for key, value in write_kanban_dry_run(
                paths["tasks_json"],
                Path(out_dir) / "kanban_dry_run",
                workspace=kanban_workspace,
                tenant=kanban_tenant,
            ).items()
        })
    if dispatch_kanban:
        paths.update({
            f"kanban_dispatch_{key}": value
            for key, value in dispatch_kanban_tasks(
                paths["tasks_json"],
                Path(out_dir) / "kanban_dispatch",
                workspace=kanban_workspace,
                tenant=kanban_tenant,
            ).items()
        })
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze social comments and dispatch agent tasks")
    parser.add_argument("--input", required=True, help="Path to exported comments: .jsonl/.json/.csv")
    parser.add_argument("--out", default="out/latest", help="Output directory")
    parser.add_argument("--platform", default="unknown", help="Source platform name")
    parser.add_argument("--platform-template", help="Known platform export template, e.g. douyin/xiaohongshu/bilibili")
    parser.add_argument(
        "--analyzer",
        choices=("rules", "llm"),
        default="rules",
        help="Analyzer mode. llm uses OpenAI-compatible env vars and falls back to rules.",
    )
    parser.add_argument("--dry-run-kanban", action="store_true", help="Write Hermes Kanban create commands without executing them")
    parser.add_argument("--dispatch-kanban", action="store_true", help="Actually create Hermes Kanban cards; also writes dry-run and dispatch reports")
    parser.add_argument("--kanban-workspace", default="scratch", help="Kanban workspace for dry-run/dispatch commands")
    parser.add_argument("--kanban-tenant", default=None, help="Optional Kanban tenant namespace")
    args = parser.parse_args()
    paths = run_pipeline(
        args.input,
        args.out,
        platform=args.platform,
        platform_template=args.platform_template,
        analyzer_mode=args.analyzer,
        dry_run_kanban=args.dry_run_kanban,
        dispatch_kanban=args.dispatch_kanban,
        kanban_workspace=args.kanban_workspace,
        kanban_tenant=args.kanban_tenant,
    )
    print("完成：")
    for name, path in paths.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
