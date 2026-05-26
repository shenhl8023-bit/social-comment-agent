import json

from social_comment_agent.watcher import format_processed_summary, scan_once


def test_watcher_processes_new_file_once(tmp_path):
    inbox = tmp_path / "inbox"
    archive = tmp_path / "archive"
    state = tmp_path / "state.json"
    inbox.mkdir()
    (inbox / "comments.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"text": "加载太慢，希望优化", "id": "1", "created_at": "2026-05-18"}, ensure_ascii=False),
                json.dumps({"text": "页面卡死加载太慢", "id": "2", "created_at": "2026-05-25"}, ensure_ascii=False),
                json.dumps({"text": "闪退崩溃", "id": "3", "created_at": "2026-05-26"}, ensure_ascii=False),
            ]
        ),
        encoding="utf-8",
    )

    first = scan_once(
        inbox,
        archive,
        state,
        platform="demo",
        dry_run_kanban=True,
        kanban_tenant="demo-tenant",
        trend=True,
        trend_bucket="week",
        knowledge_base_dir=tmp_path / "kb",
    )
    second = scan_once(
        inbox,
        archive,
        state,
        platform="demo",
        dry_run_kanban=True,
        kanban_tenant="demo-tenant",
        trend=True,
        trend_bucket="week",
    )

    assert len(first) == 1
    assert first[0]["markdown"]
    assert first[0]["kanban_dry_run"].endswith("kanban_dry_run.md")
    assert first[0]["trend_markdown"].endswith("trend_report.md")
    assert first[0]["trend_json"].endswith("trend_report.json")
    assert first[0]["knowledge_base_markdown"].endswith("knowledge_base.md")
    assert first[0]["knowledge_base_json"].endswith("knowledge_base.json")
    assert "kanban_dispatch" not in first[0]
    assert len(second) == 0
    assert state.exists()


def test_format_processed_summary_is_telegram_friendly(tmp_path):
    archive = tmp_path / "archive"
    archive.mkdir()
    markdown = archive / "pm_insights.md"
    markdown.write_text(
        "\n".join([
            "# 社交评论需求洞察报告",
            "",
            "生成时间：2026-05-25T00:00:00+00:00",
            "评论总数：3",
            "",
            "## 摘要",
            "",
            "共分析 3 条评论，主要需求集中在：功能缺口、性能与稳定性。",
            "",
            "## 1. 功能缺口（P1，score=1.4）",
            "",
            "- 问题：用户明确表达功能缺口或新增能力需求",
            "- 用户价值：让产品更贴近真实使用场景",
            "- 建议方案：梳理高频功能请求并进入需求池评审",
            "",
            "## 2. 性能与稳定性（P2，score=0.6）",
            "",
            "- 问题：用户遇到性能或稳定性问题",
        ]),
        encoding="utf-8",
    )
    trend_markdown = archive / "trend_report.md"
    trend_markdown.write_text(
        "\n".join([
            "# 社交评论需求趋势报告",
            "",
            "生成时间：2026-05-25T00:00:00+00:00",
            "聚合方式：按周",
            "当前周期：2026-W22",
            "上一周期：2026-W21",
            "有效评论总数：6",
            "当前周期评论数：4",
            "上一周期评论数：2",
            "",
            "## 摘要",
            "",
            "对比 2026-W21，2026-W22 当前周期有 4 条主题命中证据。升温主题：性能与稳定性+2。",
            "",
            "## 1. 性能与稳定性（P1）",
            "",
            "- 当前周期：3",
        ]),
        encoding="utf-8",
    )

    summary = format_processed_summary([
        {
            "input": str(tmp_path / "inbox" / "comments.csv"),
            "archive": str(archive),
            "markdown": str(markdown),
            "json": str(archive / "pm_insights.json"),
            "trend_markdown": str(trend_markdown),
            "trend_json": str(archive / "trend_report.json"),
            "kanban_dry_run": str(archive / "kanban_dry_run" / "kanban_dry_run.md"),
            "knowledge_base_markdown": str(archive / "kb" / "knowledge_base.md"),
        }
    ])

    assert "社交评论分析完成" in summary
    assert "comments.csv" in summary
    assert "评论总数：3" in summary
    assert "共分析 3 条评论" in summary
    assert "功能缺口（P1" in summary
    assert "性能与稳定性（P2" in summary
    assert "趋势：" in summary
    assert "当前周期：2026-W22" in summary
    assert "升温主题：性能与稳定性+2" in summary
    assert "性能与稳定性（P1" in summary
    assert str(trend_markdown) in summary
    assert "Kanban dry-run" in summary
    assert "知识库：" in summary
    assert str(archive / "kb" / "knowledge_base.md") in summary
    assert str(markdown) in summary
    assert '"processed"' not in summary
