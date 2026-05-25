import json

from social_comment_agent.compare import compare_analyzers, comparison_to_markdown
from social_comment_agent.llm_analyzer import LLMConfig
from social_comment_agent.models import Comment


class _FakeResponse:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._body


def _openai_response(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def test_compare_analyzers_reports_overlap_and_unique_topics(monkeypatch):
    def fake_urlopen(request, timeout):
        content = json.dumps(
            {
                "insights": [
                    {
                        "title": "客服与信任",
                        "problem": "客服回复慢且充值额度未到账",
                        "user_value": "提升付费信任",
                        "priority": "P1",
                        "suggested_solution": "建立充值状态追踪和客服 SLA",
                        "score": 0.9,
                        "evidence_comment_ids": ["c1"],
                    },
                    {
                        "title": "大文件导入稳定性",
                        "problem": "导入大文件时卡死",
                        "user_value": "保证核心流程完成",
                        "priority": "P1",
                        "suggested_solution": "异步导入并支持任务恢复",
                        "score": 0.8,
                        "evidence_comment_ids": ["c2"],
                    },
                ]
            },
            ensure_ascii=False,
        )
        return _FakeResponse(_openai_response(content))

    monkeypatch.setattr("social_comment_agent.llm_analyzer.urllib.request.urlopen", fake_urlopen)
    comments = [
        Comment("demo", "p1", "c1", "u1", "客服回复太慢了，充值后模型额度没到账没人处理"),
        Comment("demo", "p1", "c2", "u2", "大文件导入时页面卡死，刷新后任务也找不到了"),
    ]

    result = compare_analyzers(
        comments,
        llm_config=LLMConfig(endpoint="https://llm.example/v1/chat/completions", api_key="secret", model="demo-model"),
    )

    assert result.total_comments == 2
    assert result.rules_titles == ["性能与稳定性", "客服与信任", "易用性"]
    assert result.llm_titles == ["客服与信任", "大文件导入稳定性"]
    assert result.overlap_titles == ["客服与信任"]
    assert result.llm_only_titles == ["大文件导入稳定性"]
    assert result.rules_only_titles == ["性能与稳定性", "易用性"]

    markdown = comparison_to_markdown(result)
    assert "# LLM vs 规则版分析对比" in markdown
    assert "重合主题：1" in markdown
    assert "LLM 独有主题" in markdown
    assert "大文件导入稳定性" in markdown
