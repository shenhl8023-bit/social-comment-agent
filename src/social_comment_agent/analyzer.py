from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .models import AnalysisReport, Comment, Insight


@dataclass(frozen=True)
class DemandTheme:
    name: str
    keywords: tuple[str, ...]
    problem: str
    value: str
    solution: str


THEMES = (
    DemandTheme("性能与稳定性", ("卡", "慢", "闪退", "崩", "加载", "延迟"), "用户遇到性能或稳定性问题", "减少流失并提升核心流程完成率", "建立性能监控、优化关键路径并补充异常恢复"),
    DemandTheme("价格与付费", ("贵", "收费", "会员", "价格", "退款", "优惠"), "用户对价格、会员或退款机制有疑虑", "提升付费转化和信任感", "优化套餐说明、退款入口和价格权益展示"),
    DemandTheme("功能缺口", ("希望", "能不能", "建议", "没有", "缺", "加一个", "支持"), "用户明确表达功能缺口或新增能力需求", "让产品更贴近真实使用场景", "梳理高频功能请求并进入需求池评审"),
    DemandTheme("易用性", ("不会", "找不到", "麻烦", "复杂", "入口", "教程"), "用户在理解或操作路径上受阻", "降低新手门槛并减少客服压力", "简化入口、增加引导和关键步骤提示"),
    DemandTheme("客服与信任", ("客服", "没人回", "投诉", "骗子", "售后", "联系"), "用户对服务响应和可信度有担忧", "恢复用户信任并减少负面传播", "建立客服 SLA、工单追踪和透明状态反馈"),
)


class DemandAnalyzer:
    """Rule-based analyzer with an LLM-compatible boundary.

    生产环境可把 analyze() 内部替换为 LLM 调用；输入输出模型保持不变。
    """

    def analyze(self, comments: list[Comment], top_n: int = 5) -> AnalysisReport:
        buckets: dict[DemandTheme, list[Comment]] = defaultdict(list)
        for comment in comments:
            text = comment.normalized_text().lower()
            for theme in THEMES:
                if any(keyword.lower() in text for keyword in theme.keywords):
                    buckets[theme].append(comment)

        insights: list[Insight] = []
        for theme, evidence in buckets.items():
            evidence = sorted(evidence, key=_comment_weight, reverse=True)
            score = round(sum(_comment_weight(c) for c in evidence) / max(len(comments), 1), 2)
            insights.append(
                Insight(
                    title=theme.name,
                    problem=theme.problem,
                    user_value=theme.value,
                    priority=_priority(score, len(evidence)),
                    evidence=evidence[:5],
                    suggested_solution=theme.solution,
                    score=score,
                )
            )
        insights.sort(key=lambda i: (i.priority == "P0", i.priority == "P1", i.score), reverse=True)
        insights = insights[:top_n]
        summary = _summary(len(comments), insights)
        return AnalysisReport.create(total_comments=len(comments), insights=insights, summary=summary)


def _comment_weight(comment: Comment) -> float:
    likes = max(comment.metrics.get("likes", comment.metrics.get("like_count", comment.metrics.get("点赞数", 0))), 0)
    replies = max(comment.metrics.get("replies", comment.metrics.get("reply_count", 0)), 0)
    return 1 + min(likes, 100) / 20 + min(replies, 50) / 10


def _priority(score: float, count: int) -> str:
    if count >= 3 and score >= 1.5:
        return "P0"
    if count >= 2 or score >= 1.0:
        return "P1"
    return "P2"


def _summary(total: int, insights: list[Insight]) -> str:
    if not insights:
        return f"共分析 {total} 条评论，未发现足够集中的需求主题。"
    top = "、".join(i.title for i in insights[:3])
    return f"共分析 {total} 条评论，主要需求集中在：{top}。建议产品经理优先评审 P0/P1 主题。"
