#!/usr/bin/env bash
set -euo pipefail

# Script-only watcher wrapper suitable for Hermes cron --no-agent.
# It prints a Telegram-friendly digest only when new authorized exports are processed.

ROOT="${SOCIAL_COMMENT_AGENT_ROOT:-/mnt/d/CodeProj/social-comment-agent}"
INBOX="${SOCIAL_COMMENT_AGENT_INBOX:-$ROOT/data/inbox}"
ARCHIVE="${SOCIAL_COMMENT_AGENT_ARCHIVE:-$ROOT/archive}"
STATE="${SOCIAL_COMMENT_AGENT_STATE:-$ROOT/.social_comment_watch_state.json}"
PLATFORM="${SOCIAL_COMMENT_AGENT_PLATFORM:-unknown}"
ANALYZER="${SOCIAL_COMMENT_AGENT_ANALYZER:-rules}"
KANBAN_WORKSPACE="${SOCIAL_COMMENT_AGENT_KANBAN_WORKSPACE:-scratch}"
KANBAN_TENANT="${SOCIAL_COMMENT_AGENT_KANBAN_TENANT:-social-comment-agent}"
KANBAN_MODE="${SOCIAL_COMMENT_AGENT_KANBAN_MODE:-none}" # none | dry-run | dispatch

mkdir -p "$INBOX"

args=(
  --inbox "$INBOX"
  --archive "$ARCHIVE"
  --state "$STATE"
  --platform "$PLATFORM"
  --analyzer "$ANALYZER"
  --kanban-workspace "$KANBAN_WORKSPACE"
  --kanban-tenant "$KANBAN_TENANT"
)

case "$KANBAN_MODE" in
  none)
    ;;
  dry-run)
    args+=(--dry-run-kanban)
    ;;
  dispatch)
    args+=(--dispatch-kanban)
    ;;
  *)
    echo "Invalid SOCIAL_COMMENT_AGENT_KANBAN_MODE: $KANBAN_MODE" >&2
    exit 2
    ;;
esac

cd "$ROOT"
PYTHONPATH=src python -m social_comment_agent.watcher "${args[@]}"
