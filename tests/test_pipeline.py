import json

from social_comment_agent.cli import run_pipeline


def test_pipeline_generates_reports_and_agent_tasks(tmp_path):
    data = tmp_path / "comments.jsonl"
    data.write_text(
        "\n".join([
            json.dumps({"text": "加载太慢，希望优化", "id": "1", "likes": 30}, ensure_ascii=False),
            json.dumps({"text": "建议加一个导出功能", "id": "2", "likes": 30}, ensure_ascii=False),
        ]),
        encoding="utf-8",
    )
    out = tmp_path / "out"
    paths = run_pipeline(data, out, platform="demo")
    assert paths["markdown"].exists()
    assert paths["json"].exists()
    assert paths["product_manager"].exists()
    assert paths["developer"].exists()
    assert paths["tester"].exists()
    assert paths["acceptance"].exists()
    assert "社交评论需求洞察报告" in paths["markdown"].read_text(encoding="utf-8")


def test_package_module_entrypoint_runs_pipeline(tmp_path):
    data = tmp_path / "comments.jsonl"
    data.write_text(
        json.dumps({"text": "希望支持导出报表", "id": "1"}, ensure_ascii=False),
        encoding="utf-8",
    )
    out = tmp_path / "entrypoint-out"

    from subprocess import run
    import sys

    result = run(
        [
            sys.executable,
            "-m",
            "social_comment_agent",
            "--input",
            str(data),
            "--out",
            str(out),
            "--platform",
            "demo",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "完成：" in result.stdout
    assert (out / "pm_insights.md").exists()


def test_package_module_entrypoint_supports_knowledge_base_search(tmp_path):
    from social_comment_agent.knowledge_base import build_knowledge_base
    from subprocess import run
    import sys

    archive = tmp_path / "archive"
    run_dir = archive / "run" / "comments"
    run_dir.mkdir(parents=True)
    (run_dir / "pm_insights.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-05-28T00:00:00+00:00",
                "total_comments": 1,
                "summary": "主要需求集中在：功能缺口",
                "insights": [
                    {
                        "title": "功能缺口",
                        "problem": "用户需要导出报表",
                        "user_value": "减少手工整理",
                        "priority": "P1",
                        "suggested_solution": "增加报表导出 MVP",
                        "score": 1.0,
                        "evidence": [{"text": "希望支持导出报表"}],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    index = build_knowledge_base(archive, tmp_path / "kb")["index_json"]

    result = run(
        [
            sys.executable,
            "-m",
            "social_comment_agent",
            "knowledge-base",
            "search",
            "导出 报表",
            "--index",
            str(index),
            "--limit",
            "1",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "功能缺口" in result.stdout
