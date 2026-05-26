from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .analyzer import DemandAnalyzer
from .archiver import archive_report
from .collector import dedupe_comments, load_comments
from .llm_analyzer import LLMAnalyzer
from .platform_templates import get_platform_template
from .task_router import write_agent_tasks
from .kanban import dispatch_kanban_tasks, write_kanban_dry_run
from .knowledge_base import build_knowledge_base, search_knowledge_base


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
    knowledge_base_dir: str | Path | None = None,
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
    if knowledge_base_dir:
        paths.update({
            f"knowledge_base_{key}": value
            for key, value in build_knowledge_base(Path(out_dir).parent, knowledge_base_dir).items()
        })
    return paths


def print_knowledge_base_search_results(results: list[dict[str, Any]]) -> None:
    if not results:
        print("未找到匹配的历史洞察。")
        return
    for idx, item in enumerate(results, start=1):
        print(f"## {idx}. {item.get('title', '未命名洞察')}（{item.get('priority', '')}，score={item.get('score', 0)}）")
        print(f"匹配词：{', '.join(str(term) for term in item.get('matched_terms', []))}")
        problem = str(item.get("problem", "")).strip()
        if problem:
            print(f"问题：{problem}")
        solution = str(item.get("suggested_solution", "")).strip()
        if solution:
            print(f"建议：{solution}")
        evidence = [str(text) for text in item.get("evidence_texts", []) if str(text).strip()]
        if evidence:
            print("证据：")
            for text in evidence[:3]:
                print(f"- {text}")
        source = str(item.get("source_report", "")).strip()
        if source:
            print(f"来源：{source}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze social comments and dispatch agent tasks")
    subparsers = parser.add_subparsers(dest="command")
    kb_parser = subparsers.add_parser("knowledge-base", help="PM insight knowledge base commands")
    kb_subparsers = kb_parser.add_subparsers(dest="knowledge_base_command")
    kb_search = kb_subparsers.add_parser("search", help="Search archived PM insight knowledge base")
    kb_search.add_argument("query", help="Keyword query, e.g. '导出 报表'")
    kb_search.add_argument("--index", default="knowledge_base/knowledge_base.json", help="Path to knowledge_base.json")
    kb_search.add_argument("--limit", type=int, default=10, help="Maximum number of matches")

    parser.add_argument("--input", required=False, help="Path to exported comments: .jsonl/.json/.csv")
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
    parser.add_argument("--knowledge-base", help="Build/update a local PM insight knowledge base directory")
    args = parser.parse_args()
    if args.command == "knowledge-base":
        if args.knowledge_base_command == "search":
            results = search_knowledge_base(args.index, args.query, limit=args.limit)
            print_knowledge_base_search_results(results)
            return
        kb_parser.print_help()
        return

    if not args.input:
        parser.error("the following arguments are required: --input")

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
        knowledge_base_dir=args.knowledge_base,
    )
    print("完成：")
    for name, path in paths.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
