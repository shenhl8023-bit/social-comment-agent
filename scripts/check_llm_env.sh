#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${1:-$PROJECT_DIR/.env.local}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

python - <<'PY'
import os
import sys

endpoint = os.getenv("SOCIAL_COMMENT_LLM_ENDPOINT") or os.getenv("OPENAI_BASE_URL")
api_key = os.getenv("SOCIAL_COMMENT_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
model = os.getenv("SOCIAL_COMMENT_LLM_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

print("Social Comment Agent LLM environment check")
print(f"- endpoint: {'configured' if endpoint else 'missing'}")
print(f"- api_key: {'configured' if api_key else 'missing'}")
print(f"- model: {model}")

if not endpoint or not api_key:
    print("\nLLM is not fully configured. --analyzer llm will safely fall back to rule-based analysis.")
    sys.exit(0)

print("\nLLM is configured. You can run --analyzer llm or social_comment_agent.compare.")
PY
