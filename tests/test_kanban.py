from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from social_comment_agent.cli import run_pipeline
from social_comment_agent.kanban import build_kanban_commands, dispatch_kanban_tasks, write_kanban_dry_run


def test_kanban_dry_run_generates_idempotent_hermes_commands(tmp_path):
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

    commands = build_kanban_commands(paths["tasks_json"], workspace="scratch", tenant="demo-tenant")

    assert commands
    assert commands[0].startswith("hermes kanban create ")
    assert "--workspace scratch" in commands[0]
    assert "--tenant demo-tenant" in commands[0]
    assert "--idempotency-key" in commands[0]
    assert "--assignee product_manager" in "\n".join(commands)
    assert "--assignee developer" in "\n".join(commands)


def test_write_kanban_dry_run_artifacts(tmp_path):
    tasks_path = _write_single_task(tmp_path)

    output = write_kanban_dry_run(tasks_path, tmp_path / "dry-run", workspace="dir:/tmp/project")

    assert output["json"].exists()
    assert output["markdown"].exists()
    payload = json.loads(output["json"].read_text(encoding="utf-8"))
    assert payload[0]["task"]["agent"] == "tester"
    assert "hermes kanban create" in payload[0]["command"]
    assert "# Kanban dry-run" in output["markdown"].read_text(encoding="utf-8")


def test_dispatch_kanban_tasks_uses_safe_argv_and_writes_report(tmp_path):
    tasks_path = _write_single_task(tmp_path)
    calls = []

    def fake_runner(argv, capture_output, text, check):
        calls.append({
            "argv": argv,
            "capture_output": capture_output,
            "text": text,
            "check": check,
        })
        return subprocess.CompletedProcess(argv, 0, stdout='{"id":"task-1"}', stderr="")

    output = dispatch_kanban_tasks(
        tasks_path,
        tmp_path / "dispatch",
        workspace="scratch",
        tenant="demo-tenant",
        runner=fake_runner,
    )

    assert calls
    argv = calls[0]["argv"]
    assert argv[:3] == ["hermes", "kanban", "create"]
    assert "--json" in argv
    assert "--tenant" in argv
    assert "demo-tenant" in argv
    assert calls[0]["check"] is False
    assert output["json"].exists()
    payload = json.loads(output["json"].read_text(encoding="utf-8"))
    assert payload[0]["created"] is True
    assert payload[0]["json"] == {"id": "task-1"}
    assert "# Kanban dispatch report" in output["markdown"].read_text(encoding="utf-8")


def test_dispatch_kanban_tasks_stops_and_reports_failure(tmp_path):
    tasks_path = _write_single_task(tmp_path)

    def failing_runner(argv, capture_output, text, check):
        return subprocess.CompletedProcess(argv, 2, stdout="", stderr="boom")

    with pytest.raises(RuntimeError):
        dispatch_kanban_tasks(tasks_path, tmp_path / "dispatch", runner=failing_runner)

    report = tmp_path / "dispatch" / "kanban_dispatch.json"
    assert report.exists()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload[0]["created"] is False
    assert payload[0]["stderr"] == "boom"


def _write_single_task(tmp_path: Path) -> Path:
    tasks_path = tmp_path / "kanban_tasks.json"
    tasks_path.write_text(
        json.dumps([
            {
                "agent": "tester",
                "title": "测试设计：性能与稳定性",
                "objective": "覆盖主流程、异常流程和回归风险",
                "context": "需求主题：性能与稳定性",
                "acceptance_criteria": ["列出功能用例", "标记 P0/P1 风险"],
                "source_insights": ["性能与稳定性"],
            }
        ], ensure_ascii=False),
        encoding="utf-8",
    )
    return tasks_path
