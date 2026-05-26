#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="${PYTHONPATH:-src}"
INPUT="${1:-data/samples/realistic_product_feedback_30.csv}"
OUT_ROOT="${SOCIAL_COMMENT_REALISTIC_OUT:-out/realistic-demo}"
PLATFORM="${SOCIAL_COMMENT_DEMO_PLATFORM:-authorized-export}"
WORKSPACE="${SOCIAL_COMMENT_KANBAN_WORKSPACE:-/mnt/d/CodeProj/social-comment-agent}"
TENANT="${SOCIAL_COMMENT_KANBAN_TENANT:-social-comment-agent}"

if [[ ! -f "$INPUT" ]]; then
  echo "Realistic demo input not found: $INPUT" >&2
  exit 1
fi

rm -rf "$OUT_ROOT"
mkdir -p "$OUT_ROOT"

python -m social_comment_agent.cli \
  --input "$INPUT" \
  --out "$OUT_ROOT/rules-kanban" \
  --platform "$PLATFORM" \
  --analyzer rules \
  --dry-run-kanban \
  --kanban-workspace "$WORKSPACE" \
  --kanban-tenant "$TENANT"

python -m social_comment_agent.cli \
  --input "$INPUT" \
  --out "$OUT_ROOT/llm-fallback" \
  --platform "$PLATFORM" \
  --analyzer llm

python -m social_comment_agent.compare \
  --input "$INPUT" \
  --out "$OUT_ROOT/analysis_comparison.md" \
  --platform "$PLATFORM"

python - <<'PY'
from pathlib import Path
import json
root = Path("out/realistic-demo")
report = json.loads((root / "rules-kanban" / "pm_insights.json").read_text(encoding="utf-8"))
dry_run = root / "rules-kanban" / "kanban_dry_run" / "kanban_dry_run.md"
print("Realistic demo completed")
print(f"- comments: {report['total_comments']}")
print("- top insights:")
for item in report["insights"][:5]:
    print(f"  - {item['priority']} {item['title']} score={item['score']} evidence={len(item['evidence'])}")
print(f"- PM report: {root / 'rules-kanban' / 'pm_insights.md'}")
print(f"- Kanban dry-run: {dry_run}")
print(f"- Comparison: {root / 'analysis_comparison.md'}")
PY
