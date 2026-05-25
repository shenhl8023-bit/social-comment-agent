import json

from social_comment_agent.cli import run_pipeline
from social_comment_agent.llm_analyzer import LLMAnalyzer
from social_comment_agent.models import Comment


def test_llm_analyzer_falls_back_without_config(monkeypatch):
    monkeypatch.delenv("SOCIAL_COMMENT_LLM_ENDPOINT", raising=False)
    monkeypatch.delenv("SOCIAL_COMMENT_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    report = LLMAnalyzer().analyze([
        Comment(platform="demo", post_id="p1", comment_id="c1", author="u", text="加载太慢，希望优化")
    ])
    assert report.insights
    assert report.insights[0].title == "性能与稳定性"


def test_pipeline_llm_mode_falls_back_without_config(tmp_path, monkeypatch):
    monkeypatch.delenv("SOCIAL_COMMENT_LLM_ENDPOINT", raising=False)
    monkeypatch.delenv("SOCIAL_COMMENT_LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    data = tmp_path / "comments.jsonl"
    data.write_text(json.dumps({"text": "建议加一个导出功能", "id": "1"}, ensure_ascii=False), encoding="utf-8")
    paths = run_pipeline(data, tmp_path / "out", platform="demo", analyzer_mode="llm")
    assert paths["markdown"].exists()
    assert "功能缺口" in paths["markdown"].read_text(encoding="utf-8")
