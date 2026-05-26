from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Sequence

from .models import AgentTask

Runner = Callable[..., subprocess.CompletedProcess[str]]


def task_to_body(task: AgentTask) -> str:
    lines = [
        task.objective,
        "",
        "## 上下文",
        task.context,
        "",
        "## 验收标准",
        *[f"- {item}" for item in task.acceptance_criteria],
        "",
        "## 来源洞察",
        *[f"- {item}" for item in task.source_insights],
        "",
        "## 合规提醒",
        "仅处理用户授权导出/官方 API 数据，不绕过平台登录、验证码、反爬、风控或访问限制。",
    ]
    return "\n".join(lines)


def idempotency_key(task: AgentTask) -> str:
    basis = json.dumps(asdict(task), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def argv_for_task(
    task: AgentTask,
    workspace: str = "scratch",
    tenant: str | None = None,
    json_output: bool = False,
) -> list[str]:
    argv = [
        "hermes",
        "kanban",
        "create",
        task.title,
        "--body",
        task_to_body(task),
        "--assignee",
        task.agent,
        "--workspace",
        workspace,
        "--idempotency-key",
        idempotency_key(task),
    ]
    if tenant:
        argv.extend(["--tenant", tenant])
    if json_output:
        argv.append("--json")
    return argv


def command_for_task(task: AgentTask, workspace: str = "scratch", tenant: str | None = None) -> str:
    return " ".join(shlex.quote(part) for part in argv_for_task(task, workspace=workspace, tenant=tenant))


def load_tasks(path: str | Path) -> list[AgentTask]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Kanban tasks JSON must contain a list")
    return [AgentTask(**item) for item in raw]


def build_kanban_commands(tasks_path: str | Path, workspace: str = "scratch", tenant: str | None = None) -> list[str]:
    return [command_for_task(task, workspace=workspace, tenant=tenant) for task in load_tasks(tasks_path)]


def write_kanban_dry_run(
    tasks_path: str | Path,
    out_dir: str | Path,
    workspace: str = "scratch",
    tenant: str | None = None,
) -> dict[str, Path]:
    tasks = load_tasks(tasks_path)
    payload: list[dict[str, Any]] = []
    for task in tasks:
        payload.append({
            "task": asdict(task),
            "workspace": workspace,
            "tenant": tenant,
            "idempotency_key": idempotency_key(task),
            "command": command_for_task(task, workspace=workspace, tenant=tenant),
        })

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "kanban_dry_run.json"
    md_path = out / "kanban_dry_run.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_dry_run_markdown(payload), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def dispatch_kanban_tasks(
    tasks_path: str | Path,
    out_dir: str | Path,
    workspace: str = "scratch",
    tenant: str | None = None,
    runner: Runner = subprocess.run,
) -> dict[str, Path]:
    """Create Hermes Kanban cards and write an auditable dispatch report.

    This is intentionally a separate explicit step from dry-run generation so
    callers cannot accidentally create tasks without opting in.
    """
    tasks = load_tasks(tasks_path)
    results: list[dict[str, Any]] = []
    for task in tasks:
        argv = argv_for_task(task, workspace=workspace, tenant=tenant, json_output=True)
        completed = runner(argv, capture_output=True, text=True, check=False)
        item: dict[str, Any] = {
            "task": asdict(task),
            "workspace": workspace,
            "tenant": tenant,
            "idempotency_key": idempotency_key(task),
            "argv": argv,
            "command": " ".join(shlex.quote(part) for part in argv),
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "created": completed.returncode == 0,
        }
        if completed.stdout.strip():
            item["json"] = _try_parse_json(completed.stdout)
        results.append(item)
        if completed.returncode != 0:
            break

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "kanban_dispatch.json"
    md_path = out / "kanban_dispatch.md"
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_dispatch_markdown(results), encoding="utf-8")

    failed = [item for item in results if item["returncode"] != 0]
    if failed:
        first = failed[0]
        raise RuntimeError(
            f"Kanban dispatch failed for idempotency_key={first['idempotency_key']}; "
            f"see {json_path} and {md_path}"
        )
    return {"json": json_path, "markdown": md_path}


def _try_parse_json(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _dry_run_markdown(payload: list[dict[str, Any]]) -> str:
    lines = [
        "# Kanban dry-run",
        "",
        "以下命令仅供审阅，未实际创建 Hermes Kanban 卡片。确认后可逐条执行或用 --dispatch-kanban 自动执行。",
        "",
    ]
    for idx, item in enumerate(payload, start=1):
        task = item["task"]
        lines.extend([
            f"## {idx}. {task['agent']} — {task['title']}",
            "",
            f"- idempotency_key: `{item['idempotency_key']}`",
            f"- workspace: `{item['workspace']}`",
            f"- tenant: `{item['tenant'] or ''}`",
            "",
            "```bash",
            item["command"],
            "```",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def _dispatch_markdown(results: Sequence[dict[str, Any]]) -> str:
    lines = [
        "# Kanban dispatch report",
        "",
        "此报告记录 --dispatch-kanban 实际执行结果。",
        "",
    ]
    for idx, item in enumerate(results, start=1):
        task = item["task"]
        status = "created" if item["created"] else "failed"
        lines.extend([
            f"## {idx}. {status}: {task['agent']} — {task['title']}",
            "",
            f"- idempotency_key: `{item['idempotency_key']}`",
            f"- returncode: `{item['returncode']}`",
            "",
            "```bash",
            item["command"],
            "```",
            "",
        ])
        if item.get("stdout"):
            lines.extend(["stdout:", "```", item["stdout"].strip(), "```", ""])
        if item.get("stderr"):
            lines.extend(["stderr:", "```", item["stderr"].strip(), "```", ""])
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate dry-run Hermes Kanban create commands from agent tasks")
    parser.add_argument("--tasks", required=True, help="Path to kanban_tasks.json")
    parser.add_argument("--out", default="out/kanban-dry-run", help="Output directory")
    parser.add_argument("--workspace", default="scratch", help="Kanban workspace, e.g. scratch or dir:/path")
    parser.add_argument("--tenant", default=None, help="Optional tenant namespace")
    parser.add_argument("--dispatch", action="store_true", help="Actually create Hermes Kanban cards and write a dispatch report")
    args = parser.parse_args()
    paths = write_kanban_dry_run(args.tasks, args.out, workspace=args.workspace, tenant=args.tenant)
    if args.dispatch:
        paths.update({
            f"dispatch_{key}": value
            for key, value in dispatch_kanban_tasks(args.tasks, args.out, workspace=args.workspace, tenant=args.tenant).items()
        })
    print("完成：")
    for name, path in paths.items():
        print(f"- {name}: {path}")


if __name__ == "__main__":
    main()
