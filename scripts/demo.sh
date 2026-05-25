#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="${PYTHONPATH:-src}"
INPUT="${1:-data/raw/sample_comments.jsonl}"
PLATFORM="${SOCIAL_COMMENT_DEMO_PLATFORM:-demo}"

if [[ ! -f "$INPUT" ]]; then
  echo "Demo input not found: $INPUT" >&2
  exit 1
fi

rm -rf out/demo out/demo-llm out/analysis_comparison.md

python -m social_comment_agent.cli \
  --input "$INPUT" \
  --out out/demo \
  --platform "$PLATFORM" \
  --analyzer rules

python -m social_comment_agent.cli \
  --input "$INPUT" \
  --out out/demo-llm \
  --platform "$PLATFORM" \
  --analyzer llm

python -m social_comment_agent.compare \
  --input "$INPUT" \
  --out out/analysis_comparison.md \
  --platform "$PLATFORM"

echo "Demo completed"
echo "- out/demo/pm_insights.md"
echo "- out/demo-llm/pm_insights.md"
echo "- out/analysis_comparison.md"
