import os
import subprocess
from pathlib import Path


def test_demo_script_runs_end_to_end_and_writes_expected_reports():
    repo = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"

    result = subprocess.run(
        ["bash", "scripts/demo.sh"],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert "Demo completed" in result.stdout
    assert (repo / "out" / "demo" / "pm_insights.md").exists()
    assert (repo / "out" / "demo-llm" / "pm_insights.md").exists()
    comparison = repo / "out" / "analysis_comparison.md"
    assert comparison.exists()
    assert "# LLM vs 规则版分析对比" in comparison.read_text(encoding="utf-8")
