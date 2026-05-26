from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import AnalysisReport


def report_to_markdown(report: AnalysisReport) -> str:
    lines = [
        "# 社交评论需求洞察报告",
        "",
        f"生成时间：{report.generated_at}",
        f"评论总数：{report.total_comments}",
        "",
        f"## 摘要\n\n{report.summary}",
    ]
    for idx, insight in enumerate(report.insights, start=1):
        lines.extend([
            "",
            f"## {idx}. {insight.title}（{insight.priority}，score={insight.score}）",
            "",
            f"- 问题：{insight.problem}",
            f"- 用户价值：{insight.user_value}",
            f"- 建议方案：{insight.suggested_solution}",
            "- 证据评论：",
        ])
        for comment in insight.evidence:
            lines.append(f"  - [{comment.platform}/{comment.comment_id}] {comment.author}: {comment.normalized_text()}")
    lines.append("")
    return "\n".join(lines)


def archive_report(report: AnalysisReport, out_dir: str | Path) -> dict[str, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    md_path = out / "pm_insights.md"
    json_path = out / "pm_insights.json"
    md_path.write_text(report_to_markdown(report), encoding="utf-8")
    json_path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"markdown": md_path, "json": json_path}
