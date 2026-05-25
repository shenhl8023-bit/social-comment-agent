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
