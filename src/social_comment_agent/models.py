from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Comment:
    platform: str
    post_id: str
    comment_id: str
    author: str
    text: str
    created_at: str = ""
    metrics: dict[str, int] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    def normalized_text(self) -> str:
        return " ".join(self.text.strip().split())


@dataclass(frozen=True)
class Insight:
    title: str
    problem: str
    user_value: str
    priority: str
    evidence: list[Comment]
    suggested_solution: str
    score: float


@dataclass(frozen=True)
class AgentTask:
    agent: str
    title: str
    objective: str
    context: str
    acceptance_criteria: list[str]
    source_insights: list[str]


@dataclass(frozen=True)
class AnalysisReport:
    generated_at: str
    total_comments: int
    insights: list[Insight]
    summary: str

    @classmethod
    def create(cls, total_comments: int, insights: list[Insight], summary: str) -> "AnalysisReport":
        return cls(
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_comments=total_comments,
            insights=insights,
            summary=summary,
        )
