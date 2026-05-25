import json

from social_comment_agent.watcher import format_processed_summary, scan_once


def test_watcher_processes_new_file_once(tmp_path):
    inbox = tmp_path / "inbox"
    archive = tmp_path / "archive"
    state = tmp_path / "state.json"
    inbox.mkdir()
    (inbox / "comments.jsonl").write_text(
        json.dumps({"text": "加载太慢，希望优化", "id": "1"}, ensure_ascii=False),
        encoding="utf-8",
    )

    first = scan_once(inbox, archive, state, platform="demo")
    second = scan_once(inbox, archive, state, platform="demo")

    assert len(first) == 1
    assert first[0]["markdown"]
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

    summary = format_processed_summary([
        {
            "input": str(tmp_path / "inbox" / "comments.csv"),
            "archive": str(archive),
            "markdown": str(markdown),
            "json": str(archive / "pm_insights.json"),
        }
    ])

    assert "社交评论分析完成" in summary
    assert "comments.csv" in summary
    assert "评论总数：3" in summary
    assert "共分析 3 条评论" in summary
    assert "功能缺口（P1" in summary
    assert "性能与稳定性（P2" in summary
    assert str(markdown) in summary
    assert '"processed"' not in summary
