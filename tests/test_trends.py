import json

from social_comment_agent.collector import dedupe_comments, load_comments
from social_comment_agent.models import Comment
from social_comment_agent.trends import analyze_trends, run_trend_pipeline, trend_report_to_markdown


def test_analyze_weekly_trends_detects_rising_theme():
    comments = [
        Comment("x", "p", "1", "u", "希望导出Excel", created_at="2026-05-18 09:00:00"),
        Comment("x", "p", "2", "u", "页面卡死加载太慢", created_at="2026-05-25 09:00:00"),
        Comment("x", "p", "3", "u", "闪退崩溃", created_at="2026-05-26 09:00:00"),
        Comment("x", "p", "4", "u", "大文件导入太慢", created_at="2026-05-27 09:00:00"),
    ]
    report = analyze_trends(comments, bucket="week")

    assert report.current_period == "2026-W22"
    assert report.previous_period == "2026-W21"
    stability = next(t for t in report.themes if t.title == "性能与稳定性")
    assert stability.current_count == 3
    assert stability.previous_count == 0
    assert stability.delta == 3
    assert stability.priority == "P0"
    assert stability.change_rate is None


def test_analyze_monthly_trends_handles_cooling_theme():
    comments = [
        Comment("x", "p", "1", "u", "会员价格太贵", created_at="2026-04-10"),
        Comment("x", "p", "2", "u", "退款入口找不到", created_at="2026-04-11"),
        Comment("x", "p", "3", "u", "希望支持导出", created_at="2026-05-11"),
    ]
    report = analyze_trends(comments, bucket="month")

    assert report.current_period == "2026-05"
    assert report.previous_period == "2026-04"
    pricing = next(t for t in report.themes if t.title == "价格与付费")
    assert pricing.current_count == 0
    assert pricing.previous_count == 2
    assert pricing.delta == -2
    assert pricing.priority == "降温"


def test_trend_pipeline_writes_markdown_and_json(tmp_path):
    data = tmp_path / "comments.jsonl"
    data.write_text(
        "\n".join(
            [
                json.dumps({"text": "希望支持导出", "id": "1", "created_at": "2026-05-18"}, ensure_ascii=False),
                json.dumps({"text": "希望支持自动日报", "id": "2", "created_at": "2026-05-25"}, ensure_ascii=False),
                json.dumps({"text": "建议增加趋势分析", "id": "3", "created_at": "2026-05-26"}, ensure_ascii=False),
            ]
        ),
        encoding="utf-8",
    )
    paths = run_trend_pipeline(data, tmp_path / "out", platform="demo")

    assert paths["trend_markdown"].exists()
    assert paths["trend_json"].exists()
    markdown = paths["trend_markdown"].read_text(encoding="utf-8")
    assert "社交评论需求趋势报告" in markdown
    assert "当前周期：2026-W22" in markdown


def test_historical_sample_produces_trend_report():
    comments = dedupe_comments(load_comments("data/samples/historical_product_feedback_2weeks.csv", platform="authorized_export"))
    report = analyze_trends(comments, bucket="week")
    markdown = trend_report_to_markdown(report)

    assert report.current_period == "2026-W22"
    assert report.previous_period == "2026-W21"
    assert report.themes
    assert "趋势报告" in markdown
