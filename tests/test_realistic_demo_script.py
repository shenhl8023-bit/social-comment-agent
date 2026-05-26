import os
import subprocess
from pathlib import Path


def test_realistic_demo_script_runs_end_to_end_and_writes_kanban_dry_run():
    repo = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"

    result = subprocess.run(
        ["bash", "scripts/demo_realistic.sh"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "Realistic demo completed" in result.stdout
    assert "comments: 30" in result.stdout

    out = repo / "out" / "realistic-demo"
    assert (out / "rules-kanban" / "pm_insights.md").exists()
    assert (out / "rules-kanban" / "pm_insights.json").exists()
    assert (out / "rules-kanban" / "agent_tasks" / "dispatch_summary.md").exists()
    dry_run = out / "rules-kanban" / "kanban_dry_run" / "kanban_dry_run.md"
    assert dry_run.exists()
    assert "hermes kanban create" in dry_run.read_text(encoding="utf-8")
    assert (out / "llm-fallback" / "pm_insights.md").exists()
    assert "# LLM vs 规则版分析对比" in (out / "analysis_comparison.md").read_text(encoding="utf-8")
