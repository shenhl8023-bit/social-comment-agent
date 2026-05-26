from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .cli import run_pipeline
from .knowledge_base import build_knowledge_base
from .trends import run_trend_pipeline

SUPPORTED_SUFFIXES = {".jsonl", ".json", ".csv"}


def file_fingerprint(path: Path) -> str:
    stat = path.stat()
    basis = f"{path.resolve()}:{stat.st_size}:{int(stat.st_mtime)}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def load_state(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _extract_report_snippets(markdown_path: str | Path, max_insights: int = 5) -> dict[str, object]:
    path = Path(markdown_path)
    if not path.exists():
        return {"total": "", "summary": "", "insights": []}

    text = path.read_text(encoding="utf-8")
    total_match = re.search(r"^评论总数：.+$", text, flags=re.MULTILINE)
    summary_match = re.search(r"## 摘要\s+(.+?)(?:\n## |\Z)", text, flags=re.DOTALL)
    insight_matches = re.findall(r"^## \d+\.\s+(.+)$", text, flags=re.MULTILINE)

    summary = ""
    if summary_match:
        summary = " ".join(summary_match.group(1).strip().split())
    return {
        "total": total_match.group(0) if total_match else "",
        "summary": summary,
        "insights": insight_matches[:max_insights],
    }


def _extract_trend_snippets(markdown_path: str | Path, max_themes: int = 5) -> dict[str, object]:
    path = Path(markdown_path)
    if not path.exists():
        return {"period": "", "summary": "", "themes": []}

    text = path.read_text(encoding="utf-8")
    period_match = re.search(r"^当前周期：.+$", text, flags=re.MULTILINE)
    summary_match = re.search(r"## 摘要\s+(.+?)(?:\n## |\Z)", text, flags=re.DOTALL)
    theme_matches = re.findall(r"^## \d+\.\s+(.+)$", text, flags=re.MULTILINE)
    summary = ""
    if summary_match:
        summary = " ".join(summary_match.group(1).strip().split())
    return {
        "period": period_match.group(0) if period_match else "",
        "summary": summary,
        "themes": theme_matches[:max_themes],
    }


def format_processed_summary(processed: list[dict[str, str]]) -> str:
    if not processed:
        return ""

    lines = ["社交评论分析完成", ""]
    for idx, item in enumerate(processed, start=1):
        snippets = _extract_report_snippets(item.get("markdown", ""))
        input_name = Path(item.get("input", "")).name or item.get("input", "未知输入")
        lines.extend([
            f"## {idx}. {input_name}",
            f"归档目录：{item.get('archive', '')}",
        ])
        total = snippets["total"]
        summary = snippets["summary"]
        insights = snippets["insights"]
        if total:
            lines.append(str(total))
        if summary:
            lines.extend(["", "摘要：", str(summary)])
        if isinstance(insights, list) and insights:
            lines.extend(["", "Top 需求："])
            lines.extend(f"- {insight}" for insight in insights)
        if item.get("trend_markdown"):
            trend = _extract_trend_snippets(item["trend_markdown"])
            trend_period = trend["period"]
            trend_summary = trend["summary"]
            trend_themes = trend["themes"]
            lines.extend(["", "趋势："])
            if trend_period:
                lines.append(str(trend_period))
            if trend_summary:
                lines.append(str(trend_summary))
            if isinstance(trend_themes, list) and trend_themes:
                lines.extend(f"- {theme}" for theme in trend_themes)
            lines.append(f"趋势报告：{item['trend_markdown']}")
        if item.get("kanban_dry_run"):
            lines.extend(["", f"Kanban dry-run：{item['kanban_dry_run']}"])
        if item.get("kanban_dispatch"):
            lines.append(f"Kanban dispatch：{item['kanban_dispatch']}")
        if item.get("knowledge_base_markdown"):
            lines.append(f"知识库：{item['knowledge_base_markdown']}")
        if item.get("markdown"):
            lines.extend(["", f"完整报告：{item['markdown']}"])
        lines.append("")
    return "\n".join(lines).strip()


def scan_once(
    inbox: str | Path,
    archive_dir: str | Path,
    state_path: str | Path,
    platform: str = "unknown",
    analyzer_mode: str = "rules",
    dry_run_kanban: bool = False,
    dispatch_kanban: bool = False,
    kanban_workspace: str = "scratch",
    kanban_tenant: str | None = None,
    trend: bool = False,
    trend_bucket: str = "week",
    knowledge_base_dir: str | Path | None = None,
) -> list[dict[str, str]]:
    inbox_path = Path(inbox)
    archive_path = Path(archive_dir)
    state_file = Path(state_path)
    state = load_state(state_file)
    processed: list[dict[str, str]] = []
    if not inbox_path.exists():
        raise FileNotFoundError(f"inbox does not exist: {inbox_path}")

    for input_file in sorted(p for p in inbox_path.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES):
        fingerprint = file_fingerprint(input_file)
        key = str(input_file.resolve())
        if state.get(key) == fingerprint:
            continue
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = archive_path / timestamp / input_file.stem
        paths = run_pipeline(
            input_file,
            run_dir,
            platform=platform,
            analyzer_mode=analyzer_mode,
            dry_run_kanban=dry_run_kanban,
            dispatch_kanban=dispatch_kanban,
            kanban_workspace=kanban_workspace,
            kanban_tenant=kanban_tenant,
        )
        state[key] = fingerprint
        item = {
            "input": str(input_file),
            "archive": str(run_dir),
            "markdown": str(paths["markdown"]),
            "json": str(paths["json"]),
        }
        if trend:
            trend_paths = run_trend_pipeline(input_file, run_dir / "trends", platform=platform, bucket=trend_bucket)
            item["trend_markdown"] = str(trend_paths["trend_markdown"])
            item["trend_json"] = str(trend_paths["trend_json"])
        if "kanban_dry_run_markdown" in paths:
            item["kanban_dry_run"] = str(paths["kanban_dry_run_markdown"])
        if "kanban_dispatch_markdown" in paths:
            item["kanban_dispatch"] = str(paths["kanban_dispatch_markdown"])
        processed.append(item)
    if processed and knowledge_base_dir:
        kb_paths = build_knowledge_base(archive_path, knowledge_base_dir)
        for item in processed:
            item["knowledge_base_json"] = str(kb_paths["index_json"])
            item["knowledge_base_markdown"] = str(kb_paths["index_markdown"])
    if processed:
        save_state(state_file, state)
    return processed


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan an inbox directory for authorized social comment exports")
    parser.add_argument("--inbox", required=True, help="Directory containing .jsonl/.json/.csv exports")
    parser.add_argument("--archive", default="archive", help="Archive output directory")
    parser.add_argument("--state", default=".social_comment_watch_state.json", help="Processed-file state path")
    parser.add_argument("--platform", default="unknown", help="Source platform name")
    parser.add_argument("--analyzer", choices=("rules", "llm"), default="rules", help="Analyzer mode")
    parser.add_argument("--dry-run-kanban", action="store_true", help="Write Hermes Kanban create commands for each processed export")
    parser.add_argument("--dispatch-kanban", action="store_true", help="Actually create Hermes Kanban cards for each processed export")
    parser.add_argument("--kanban-workspace", default="scratch", help="Kanban workspace for dry-run/dispatch commands")
    parser.add_argument("--kanban-tenant", default=None, help="Optional Kanban tenant namespace")
    parser.add_argument("--trend", action="store_true", help="Also write a week/month trend report for each processed export")
    parser.add_argument("--trend-bucket", choices=("week", "month"), default="week", help="Trend aggregation bucket")
    parser.add_argument("--knowledge-base", help="Build/update a local PM insight knowledge base directory")
    args = parser.parse_args()
    processed = scan_once(
        args.inbox,
        args.archive,
        args.state,
        platform=args.platform,
        analyzer_mode=args.analyzer,
        dry_run_kanban=args.dry_run_kanban,
        dispatch_kanban=args.dispatch_kanban,
        kanban_workspace=args.kanban_workspace,
        kanban_tenant=args.kanban_tenant,
        trend=args.trend,
        trend_bucket=args.trend_bucket,
        knowledge_base_dir=args.knowledge_base,
    )
    summary = format_processed_summary(processed)
    if summary:
        print(summary)


if __name__ == "__main__":
    main()
