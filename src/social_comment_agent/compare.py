from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from .analyzer import DemandAnalyzer
from .collector import dedupe_comments, load_comments
from .llm_analyzer import LLMAnalyzer, LLMConfig
from .models import Comment


@dataclass(frozen=True)
class AnalyzerComparison:
    total_comments: int
    rules_titles: list[str]
    llm_titles: list[str]
    overlap_titles: list[str]
    rules_only_titles: list[str]
    llm_only_titles: list[str]
    rules_summary: str
    llm_summary: str


def compare_analyzers(comments: list[Comment], llm_config: LLMConfig | None = None, top_n: int = 5) -> AnalyzerComparison:
    deduped = dedupe_comments(comments)
    rules_report = DemandAnalyzer().analyze(deduped, top_n=top_n)
    llm_report = LLMAnalyzer(config=llm_config).analyze(deduped, top_n=top_n)

    rules_titles = [insight.title for insight in rules_report.insights]
    llm_titles = [insight.title for insight in llm_report.insights]
    rules_set = set(rules_titles)
    llm_set = set(llm_titles)

    return AnalyzerComparison(
        total_comments=len(deduped),
        rules_titles=rules_titles,
        llm_titles=llm_titles,
        overlap_titles=[title for title in llm_titles if title in rules_set],
        rules_only_titles=[title for title in rules_titles if title not in llm_set],
        llm_only_titles=[title for title in llm_titles if title not in rules_set],
        rules_summary=rules_report.summary,
        llm_summary=llm_report.summary,
    )


def comparison_to_markdown(comparison: AnalyzerComparison) -> str:
    lines = [
        "# LLM vs 规则版分析对比",
        "",
        f"评论总数：{comparison.total_comments}",
        f"规则版主题数：{len(comparison.rules_titles)}",
        f"LLM 主题数：{len(comparison.llm_titles)}",
        f"重合主题：{len(comparison.overlap_titles)}",
        "",
        "## 规则版摘要",
        "",
        comparison.rules_summary,
        "",
        "## LLM 摘要",
        "",
        comparison.llm_summary,
        "",
        "## 重合主题",
        "",
        *_bullet_lines(comparison.overlap_titles),
        "",
        "## 规则版独有主题",
        "",
        *_bullet_lines(comparison.rules_only_titles),
        "",
        "## LLM 独有主题",
        "",
        *_bullet_lines(comparison.llm_only_titles),
        "",
    ]
    return "\n".join(lines)


def run_comparison(input_path: str | Path, out_path: str | Path, platform: str = "unknown", top_n: int = 5) -> Path:
    comments = load_comments(input_path, platform=platform)
    comparison = compare_analyzers(comments, top_n=top_n)
    output = Path(out_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(comparison_to_markdown(comparison), encoding="utf-8")
    return output


def _bullet_lines(items: list[str]) -> list[str]:
    if not items:
        return ["- 无"]
    return [f"- {item}" for item in items]


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare rule-based and LLM social comment analysis outputs")
    parser.add_argument("--input", required=True, help="Path to exported comments: .jsonl/.json/.csv")
    parser.add_argument("--out", default="out/analysis_comparison.md", help="Output markdown path")
    parser.add_argument("--platform", default="unknown", help="Source platform name")
    parser.add_argument("--top-n", type=int, default=5, help="Max insights per analyzer")
    args = parser.parse_args()
    path = run_comparison(args.input, args.out, platform=args.platform, top_n=args.top_n)
    print(f"完成：{path}")


if __name__ == "__main__":
    main()
