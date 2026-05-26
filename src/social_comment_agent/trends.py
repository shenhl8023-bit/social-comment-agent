from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .analyzer import DemandAnalyzer
from .collector import dedupe_comments, load_comments
from .models import Comment


@dataclass(frozen=True)
class ThemeTrend:
    title: str
    current_count: int
    previous_count: int
    delta: int
    change_rate: float | None
    priority: str
    top_evidence: list[Comment] = field(default_factory=list)


@dataclass(frozen=True)
class TrendReport:
    generated_at: str
    bucket: str
    current_period: str
    previous_period: str | None
    total_comments: int
    current_comments: int
    previous_comments: int
    themes: list[ThemeTrend]
    summary: str

    @classmethod
    def create(
        cls,
        bucket: str,
        current_period: str,
        previous_period: str | None,
        total_comments: int,
        current_comments: int,
        previous_comments: int,
        themes: list[ThemeTrend],
        summary: str,
    ) -> "TrendReport":
        return cls(
            generated_at=datetime.now(timezone.utc).isoformat(),
            bucket=bucket,
            current_period=current_period,
            previous_period=previous_period,
            total_comments=total_comments,
            current_comments=current_comments,
            previous_comments=previous_comments,
            themes=themes,
            summary=summary,
        )


def analyze_trends(comments: Iterable[Comment], bucket: str = "week", top_n: int = 5) -> TrendReport:
    comments = [c for c in comments if _period_key(c.created_at, bucket)]
    periods: dict[str, list[Comment]] = defaultdict(list)
    for comment in comments:
        periods[_period_key(comment.created_at, bucket)].append(comment)

    ordered_periods = sorted(periods)
    if not ordered_periods:
        return TrendReport.create(
            bucket=bucket,
            current_period="",
            previous_period=None,
            total_comments=0,
            current_comments=0,
            previous_comments=0,
            themes=[],
            summary="未发现带有效 created_at 的评论，无法生成趋势报告。",
        )

    current_period = ordered_periods[-1]
    previous_period = ordered_periods[-2] if len(ordered_periods) >= 2 else None
    current_comments = periods[current_period]
    previous_comments = periods[previous_period] if previous_period else []

    current_theme_comments = _comments_by_theme(current_comments)
    previous_theme_comments = _comments_by_theme(previous_comments)
    previous_counts = {title: len(items) for title, items in previous_theme_comments.items()}

    # Include disappeared themes too, so PM can see what cooled down.
    all_titles = set(current_theme_comments) | set(previous_counts)
    trends: list[ThemeTrend] = []
    for title in all_titles:
        current_count = len(current_theme_comments.get(title, []))
        previous_count = previous_counts.get(title, 0)
        delta = current_count - previous_count
        trends.append(
            ThemeTrend(
                title=title,
                current_count=current_count,
                previous_count=previous_count,
                delta=delta,
                change_rate=_change_rate(current_count, previous_count),
                priority=_trend_priority(current_count, previous_count, delta),
                top_evidence=current_theme_comments.get(title, [])[:3],
            )
        )
    trends.sort(key=lambda t: (_priority_rank(t.priority), abs(t.delta), t.current_count), reverse=True)
    trends = trends[:top_n]
    return TrendReport.create(
        bucket=bucket,
        current_period=current_period,
        previous_period=previous_period,
        total_comments=len(comments),
        current_comments=len(current_comments),
        previous_comments=len(previous_comments),
        themes=trends,
        summary=_summary(bucket, current_period, previous_period, trends),
    )


def write_trend_report(report: TrendReport, out_dir: str | Path) -> dict[str, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    md_path = out / "trend_report.md"
    json_path = out / "trend_report.json"
    md_path.write_text(trend_report_to_markdown(report), encoding="utf-8")
    json_path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"trend_markdown": md_path, "trend_json": json_path}


def trend_report_to_markdown(report: TrendReport) -> str:
    label = "按周" if report.bucket == "week" else "按月"
    lines = [
        "# 社交评论需求趋势报告",
        "",
        f"生成时间：{report.generated_at}",
        f"聚合方式：{label}",
        f"当前周期：{report.current_period or '无'}",
        f"上一周期：{report.previous_period or '无'}",
        f"有效评论总数：{report.total_comments}",
        f"当前周期评论数：{report.current_comments}",
        f"上一周期评论数：{report.previous_comments}",
        "",
        f"## 摘要\n\n{report.summary}",
    ]
    for idx, theme in enumerate(report.themes, start=1):
        rate = "N/A" if theme.change_rate is None else f"{theme.change_rate:+.0%}"
        lines.extend([
            "",
            f"## {idx}. {theme.title}（{theme.priority}）",
            "",
            f"- 当前周期：{theme.current_count}",
            f"- 上一周期：{theme.previous_count}",
            f"- 变化：{theme.delta:+d}（{rate}）",
        ])
        if theme.top_evidence:
            lines.append("- 当前周期代表评论：")
            for comment in theme.top_evidence:
                lines.append(f"  - [{comment.platform}/{comment.comment_id}] {comment.author}: {comment.normalized_text()}")
        else:
            lines.append("- 当前周期代表评论：无（该主题本期降温或消失）")
    lines.append("")
    return "\n".join(lines)


def run_trend_pipeline(
    input_path: str | Path,
    out_dir: str | Path,
    platform: str = "unknown",
    bucket: str = "week",
    top_n: int = 5,
) -> dict[str, Path]:
    comments = dedupe_comments(load_comments(input_path, platform=platform))
    report = analyze_trends(comments, bucket=bucket, top_n=top_n)
    return write_trend_report(report, out_dir)


def _comments_by_theme(comments: list[Comment]) -> dict[str, list[Comment]]:
    report = DemandAnalyzer().analyze(comments, top_n=99)
    return {insight.title: list(insight.evidence) for insight in report.insights}


def _period_key(value: str, bucket: str) -> str:
    dt = _parse_datetime(value)
    if dt is None:
        return ""
    if bucket == "month":
        return f"{dt.year:04d}-{dt.month:02d}"
    if bucket != "week":
        raise ValueError("bucket must be week or month")
    iso = dt.isocalendar()
    return f"{iso.year:04d}-W{iso.week:02d}"


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _change_rate(current: int, previous: int) -> float | None:
    if previous == 0:
        return None if current > 0 else 0.0
    return (current - previous) / previous


def _trend_priority(current: int, previous: int, delta: int) -> str:
    if current >= 3 and (delta >= 2 or previous == 0):
        return "P0"
    if current >= 2 and delta >= 1:
        return "P1"
    if delta < 0:
        return "降温"
    return "观察"


def _priority_rank(priority: str) -> int:
    return {"P0": 4, "P1": 3, "观察": 2, "降温": 1}.get(priority, 0)


def _summary(bucket: str, current: str, previous: str | None, themes: list[ThemeTrend]) -> str:
    if not current:
        return "没有足够的时间信息生成趋势。"
    if not themes:
        return f"{current} 未发现可聚合的需求主题。"
    rising = [t for t in themes if t.delta > 0]
    cooling = [t for t in themes if t.delta < 0]
    if previous is None:
        top = "、".join(t.title for t in themes[:3])
        return f"{current} 是当前唯一可用周期，主要主题为：{top}。后续导入更多周期后可观察升降趋势。"
    parts = [f"对比 {previous}，{current} 当前周期有 {sum(t.current_count for t in themes)} 条主题命中证据。"]
    if rising:
        parts.append("升温主题：" + "、".join(f"{t.title}{t.delta:+d}" for t in rising[:3]) + "。")
    if cooling:
        parts.append("降温主题：" + "、".join(f"{t.title}{t.delta:+d}" for t in cooling[:3]) + "。")
    return "".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze week/month trend changes in authorized social comment exports")
    parser.add_argument("--input", required=True, help="Path to exported comments: .jsonl/.json/.csv")
    parser.add_argument("--out", default="out/trends", help="Output directory")
    parser.add_argument("--platform", default="unknown", help="Source platform name if input rows omit platform")
    parser.add_argument("--bucket", choices=("week", "month"), default="week", help="Trend bucket")
    parser.add_argument("--top-n", type=int, default=5, help="Number of trend themes to include")
    args = parser.parse_args()
    paths = run_trend_pipeline(args.input, args.out, platform=args.platform, bucket=args.bucket, top_n=args.top_n)
    print("趋势报告完成：")
    for name, path in paths.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
