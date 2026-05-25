from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .cli import run_pipeline

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
        paths = run_pipeline(input_file, run_dir, platform=platform, analyzer_mode=analyzer_mode)
        state[key] = fingerprint
        processed.append({
            "input": str(input_file),
            "archive": str(run_dir),
            "markdown": str(paths["markdown"]),
            "json": str(paths["json"]),
        })
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
    args = parser.parse_args()
    processed = scan_once(args.inbox, args.archive, args.state, platform=args.platform, analyzer_mode=args.analyzer)
    summary = format_processed_summary(processed)
    if summary:
        print(summary)


if __name__ == "__main__":
    main()
