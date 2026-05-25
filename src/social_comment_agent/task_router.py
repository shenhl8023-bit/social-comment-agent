from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import AgentTask, AnalysisReport, Insight


AGENT_DEFINITIONS = {
    "product_manager": "提炼需求、确定范围、输出 PRD 与优先级",
    "developer": "按 PRD 设计技术方案并实现最小可用功能",
    "tester": "设计测试用例、执行回归与边界验证",
    "acceptance": "根据业务目标和验收标准做最终验收",
}


def build_tasks(report: AnalysisReport) -> list[AgentTask]:
    tasks: list[AgentTask] = []
    for insight in report.insights:
        source = [insight.title]
        tasks.append(_pm_task(insight, source))
        tasks.append(_dev_task(insight, source))
        tasks.append(_test_task(insight, source))
        tasks.append(_acceptance_task(insight, source))
    return tasks


def write_agent_tasks(report: AnalysisReport, out_dir: str | Path) -> dict[str, Path]:
    out = Path(out_dir)
    tasks_dir = out / "agent_tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    tasks = build_tasks(report)
    grouped: dict[str, list[AgentTask]] = {}
    for task in tasks:
        grouped.setdefault(task.agent, []).append(task)

    paths: dict[str, Path] = {}
    for agent, agent_tasks in grouped.items():
        path = tasks_dir / f"{agent}.json"
        path.write_text(json.dumps([asdict(t) for t in agent_tasks], ensure_ascii=False, indent=2), encoding="utf-8")
        paths[agent] = path

    md = tasks_dir / "dispatch_summary.md"
    md.write_text(_dispatch_markdown(grouped), encoding="utf-8")
    paths["summary"] = md
    return paths


def _pm_task(i: Insight, source: list[str]) -> AgentTask:
    return AgentTask(
        agent="product_manager",
        title=f"需求评审：{i.title}",
        objective=f"判断是否立项并把用户问题转为 PRD：{i.problem}",
        context=f"优先级 {i.priority}，用户价值：{i.user_value}。建议方案：{i.suggested_solution}",
        acceptance_criteria=["完成问题定义", "明确目标用户和使用场景", "给出成功指标", "输出是否进入开发的结论"],
        source_insights=source,
    )


def _dev_task(i: Insight, source: list[str]) -> AgentTask:
    return AgentTask(
        agent="developer",
        title=f"技术方案与实现：{i.title}",
        objective="基于产品经理确认范围实现最小可用方案",
        context=f"问题：{i.problem}；建议：{i.suggested_solution}",
        acceptance_criteria=["技术方案可落地", "实现覆盖核心路径", "保留日志/埋点接口", "提供可运行演示或接口说明"],
        source_insights=source,
    )


def _test_task(i: Insight, source: list[str]) -> AgentTask:
    return AgentTask(
        agent="tester",
        title=f"测试设计：{i.title}",
        objective="覆盖主流程、异常流程和回归风险",
        context=f"需求主题：{i.title}；用户痛点：{i.problem}",
        acceptance_criteria=["列出功能用例", "列出异常/边界用例", "给出回归清单", "标记 P0/P1 风险"],
        source_insights=source,
    )


def _acceptance_task(i: Insight, source: list[str]) -> AgentTask:
    return AgentTask(
        agent="acceptance",
        title=f"业务验收：{i.title}",
        objective="验证交付是否解决评论区暴露的真实问题",
        context=f"用户价值：{i.user_value}；证据评论数：{len(i.evidence)}",
        acceptance_criteria=["验收标准可观测", "证据评论问题被覆盖", "无明显副作用", "形成上线/退回结论"],
        source_insights=source,
    )


def _dispatch_markdown(grouped: dict[str, list[AgentTask]]) -> str:
    lines = ["# Agent 任务派发清单", ""]
    for agent, tasks in grouped.items():
        lines.append(f"## {agent} — {AGENT_DEFINITIONS.get(agent, '')}")
        for task in tasks:
            lines.append(f"- {task.title}: {task.objective}")
        lines.append("")
    return "\n".join(lines)
