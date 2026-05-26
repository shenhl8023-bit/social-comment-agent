import json
import sys
from subprocess import run

from social_comment_agent.knowledge_base import build_knowledge_base, search_knowledge_base


def _write_report(run_dir, title, priority, comment_text):
    run_dir.mkdir(parents=True)
    (run_dir / "pm_insights.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-05-26T00:00:00+00:00",
                "total_comments": 2,
                "summary": f"主要需求集中在：{title}",
                "insights": [
                    {
                        "title": title,
                        "problem": f"{title} 相关问题",
                        "user_value": "提升用户体验",
                        "priority": priority,
                        "suggested_solution": "进入需求池评审",
                        "score": 1.2,
                        "evidence": [
                            {
                                "platform": "demo",
                                "post_id": "p1",
                                "comment_id": "c1",
                                "author": "u1",
                                "text": comment_text,
                                "created_at": "2026-05-26",
                                "metrics": {"likes": 10},
                                "raw": {},
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_build_knowledge_base_indexes_archived_pm_insights(tmp_path):
    archive = tmp_path / "archive"
    _write_report(archive / "20260526T000000Z" / "comments", "性能与稳定性", "P1", "加载太慢，经常闪退")
    _write_report(archive / "20260527T000000Z" / "reviews", "功能缺口", "P2", "希望支持导出报表")

    paths = build_knowledge_base(archive, tmp_path / "kb")

    index = json.loads(paths["index_json"].read_text(encoding="utf-8"))
    markdown = paths["index_markdown"].read_text(encoding="utf-8")
    assert len(index["entries"]) == 2
    assert index["entries"][0]["title"] == "性能与稳定性"
    assert index["entries"][0]["source_report"].endswith("pm_insights.json")
    assert "加载太慢，经常闪退" in index["entries"][0]["evidence_texts"]
    assert "# PM 洞察知识库" in markdown
    assert "性能与稳定性" in markdown
    assert "功能缺口" in markdown


def test_search_knowledge_base_returns_keyword_matches_ranked_by_priority(tmp_path):
    archive = tmp_path / "archive"
    _write_report(archive / "older", "功能缺口", "P2", "希望支持导出报表")
    _write_report(archive / "newer", "性能与稳定性", "P0", "导出报表时加载太慢")
    paths = build_knowledge_base(archive, tmp_path / "kb")

    results = search_knowledge_base(paths["index_json"], "导出 报表")

    assert [item["title"] for item in results] == ["性能与稳定性", "功能缺口"]
    assert results[0]["match_count"] >= results[1]["match_count"]


def test_cli_search_knowledge_base_prints_ranked_matches(tmp_path):
    archive = tmp_path / "archive"
    _write_report(archive / "older", "功能缺口", "P2", "希望支持导出报表")
    _write_report(archive / "newer", "性能与稳定性", "P0", "导出报表时加载太慢")
    paths = build_knowledge_base(archive, tmp_path / "kb")

    result = run(
        [
            sys.executable,
            "-m",
            "social_comment_agent.cli",
            "knowledge-base",
            "search",
            "导出 报表",
            "--index",
            str(paths["index_json"]),
            "--limit",
            "1",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "性能与稳定性" in result.stdout
    assert "P0" in result.stdout
    assert "导出报表时加载太慢" in result.stdout
    assert "功能缺口" not in result.stdout
