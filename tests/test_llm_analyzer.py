import json

from social_comment_agent.cli import run_pipeline
from social_comment_agent.llm_analyzer import LLMAnalyzer, LLMConfig
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


def test_llm_analyzer_uses_llm_json_and_keeps_service_issue_out_of_performance(monkeypatch):
    captured_requests = []

    def fake_urlopen(request, timeout):
        captured_requests.append((request, timeout))
        content = json.dumps(
            {
                "insights": [
                    {
                        "title": "客服与额度到账信任问题",
                        "problem": "用户充值后额度未到账且客服响应慢",
                        "user_value": "提升付费信任并减少退款投诉",
                        "priority": "P1",
                        "suggested_solution": "建立充值到账状态追踪和客服 SLA",
                        "score": 0.9,
                        "evidence_comment_ids": ["c_service"],
                    },
                    {
                        "title": "大文件导入稳定性",
                        "problem": "大文件导入时页面卡死且任务丢失",
                        "user_value": "保证核心导入流程可完成",
                        "priority": "P1",
                        "suggested_solution": "增加异步导入队列和任务恢复",
                        "score": 0.8,
                        "evidence_comment_ids": ["c_perf"],
                    },
                ]
            },
            ensure_ascii=False,
        )
        return _FakeResponse(_openai_response(content))

    monkeypatch.setattr("social_comment_agent.llm_analyzer.urllib.request.urlopen", fake_urlopen)
    comments = [
        Comment(platform="demo", post_id="p1", comment_id="c_service", author="u1", text="客服回复太慢了，充值后模型额度没到账没人处理"),
        Comment(platform="demo", post_id="p1", comment_id="c_perf", author="u2", text="大文件导入时页面卡死，刷新后任务也找不到了"),
    ]

    report = LLMAnalyzer(LLMConfig(endpoint="https://llm.example/v1/chat/completions", api_key="secret", model="demo-model")).analyze(comments)

    assert captured_requests
    assert report.summary.startswith("共分析 2 条评论，LLM 提炼出的主要需求集中在")
    assert [insight.title for insight in report.insights] == ["客服与额度到账信任问题", "大文件导入稳定性"]
    assert report.insights[0].evidence[0].comment_id == "c_service"
    assert "性能" not in report.insights[0].title


def test_llm_analyzer_accepts_json_wrapped_in_markdown_fence(monkeypatch):
    def fake_urlopen(request, timeout):
        content = """```json
{"insights":[{"title":"客服与信任","problem":"客服回复慢","user_value":"减少付费流失","priority":"P1","suggested_solution":"建立 SLA","score":0.7,"evidence_comment_ids":["c1"]}]}
```"""
        return _FakeResponse(_openai_response(content))

    monkeypatch.setattr("social_comment_agent.llm_analyzer.urllib.request.urlopen", fake_urlopen)
    comments = [Comment(platform="demo", post_id="p1", comment_id="c1", author="u", text="客服回复太慢了")]

    report = LLMAnalyzer(LLMConfig(endpoint="https://llm.example/v1/chat/completions", api_key="secret", model="demo-model")).analyze(comments)

    assert report.insights[0].title == "客服与信任"
