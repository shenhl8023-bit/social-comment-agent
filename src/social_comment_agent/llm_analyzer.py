from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .analyzer import DemandAnalyzer
from .models import AnalysisReport, Comment, Insight


SYSTEM_PROMPT = """你是一个合规的产品需求分析助手。你的任务是从授权导出的社交评论中提炼产品需求洞察。
不要建议绕过登录、验证码、反爬、付费墙或平台访问限制。输出必须是严格 JSON。"""


@dataclass(frozen=True)
class LLMConfig:
    endpoint: str
    api_key: str
    model: str
    timeout_seconds: int = 60

    @classmethod
    def from_env(cls) -> "LLMConfig | None":
        endpoint = os.getenv("SOCIAL_COMMENT_LLM_ENDPOINT") or os.getenv("OPENAI_BASE_URL")
        api_key = os.getenv("SOCIAL_COMMENT_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        model = os.getenv("SOCIAL_COMMENT_LLM_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
        if not endpoint or not api_key:
            return None
        endpoint = endpoint.rstrip("/")
        if not endpoint.endswith("/chat/completions"):
            endpoint = f"{endpoint}/chat/completions"
        return cls(endpoint=endpoint, api_key=api_key, model=model)


class LLMAnalyzer:
    """OpenAI-compatible analyzer with rule-based fallback."""

    def __init__(self, config: LLMConfig | None = None, fallback: DemandAnalyzer | None = None):
        self.config = config or LLMConfig.from_env()
        self.fallback = fallback or DemandAnalyzer()

    def analyze(self, comments: list[Comment], top_n: int = 5) -> AnalysisReport:
        if not self.config:
            return self.fallback.analyze(comments, top_n=top_n)
        try:
            insights = self._call_llm(comments, top_n=top_n)
            summary = _summary(len(comments), insights)
            return AnalysisReport.create(total_comments=len(comments), insights=insights, summary=summary)
        except Exception:
            return self.fallback.analyze(comments, top_n=top_n)

    def _call_llm(self, comments: list[Comment], top_n: int) -> list[Insight]:
        assert self.config is not None
        payload = {
            "model": self.config.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_prompt(comments, top_n)},
            ],
        }
        request = urllib.request.Request(
            self.config.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM request failed: HTTP {exc.code}: {body[:500]}") from exc
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        raw_insights = parsed.get("insights", [])
        if not isinstance(raw_insights, list):
            raise ValueError("LLM response field 'insights' must be a list")
        return [_to_insight(item, comments) for item in raw_insights[:top_n]]


def _build_prompt(comments: list[Comment], top_n: int) -> str:
    compact_comments = [
        {
            "platform": comment.platform,
            "post_id": comment.post_id,
            "comment_id": comment.comment_id,
            "author": comment.author,
            "text": comment.normalized_text(),
            "created_at": comment.created_at,
            "metrics": comment.metrics,
        }
        for comment in comments[:200]
    ]
    schema = {
        "insights": [
            {
                "title": "需求标题",
                "problem": "用户问题",
                "user_value": "用户价值",
                "priority": "P0|P1|P2",
                "suggested_solution": "建议方案",
                "score": 1.0,
                "evidence_comment_ids": ["comment_id"],
            }
        ]
    }
    return (
        f"请从以下授权导出的评论中提炼最多 {top_n} 个产品需求洞察。\n"
        "优先级规则：高频且影响核心流程为 P0，明确痛点/缺陷为 P1，低频建议为 P2。\n"
        "每个洞察必须保留证据评论 ID。\n"
        f"输出 JSON schema 示例：{json.dumps(schema, ensure_ascii=False)}\n"
        f"评论：{json.dumps(compact_comments, ensure_ascii=False)}"
    )


def _to_insight(item: dict[str, Any], comments: list[Comment]) -> Insight:
    by_id = {comment.comment_id: comment for comment in comments}
    evidence_ids = item.get("evidence_comment_ids") or []
    evidence = [by_id[str(comment_id)] for comment_id in evidence_ids if str(comment_id) in by_id]
    if not evidence and comments:
        evidence = comments[:1]
    priority = str(item.get("priority") or "P2").upper()
    if priority not in {"P0", "P1", "P2"}:
        priority = "P2"
    try:
        score = float(item.get("score", len(evidence)))
    except (TypeError, ValueError):
        score = float(len(evidence))
    return Insight(
        title=str(item.get("title") or "未命名需求"),
        problem=str(item.get("problem") or "用户评论中出现未归类问题"),
        user_value=str(item.get("user_value") or "提升用户体验"),
        priority=priority,
        evidence=evidence[:5],
        suggested_solution=str(item.get("suggested_solution") or "进入需求池进一步评审"),
        score=round(score, 2),
    )


def _summary(total: int, insights: list[Insight]) -> str:
    if not insights:
        return f"共分析 {total} 条评论，未发现足够集中的需求主题。"
    top = "、".join(i.title for i in insights[:3])
    return f"共分析 {total} 条评论，LLM 提炼出的主要需求集中在：{top}。建议产品经理优先评审 P0/P1 主题。"
