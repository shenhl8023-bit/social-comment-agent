# Social Comment Agent

本项目是一个“社交平台评论区 → 需求洞察 → 产品经理归档 → 子 Agent 任务派发”的本地自动化 MVP。

## 合规边界

- 默认读取平台后台、官方 API、数据工具或人工导出的 `.jsonl/.json/.csv` 评论文件。
- 不内置绕过登录、验证码、反爬、风控的爬虫。
- 后续如果接入抖音/小红书/B站等平台，应优先用官方开放平台或用户授权导出。

## 一键运行

```bash
cd /mnt/d/CodeProj/social-comment-agent
PYTHONPATH=src python -m social_comment_agent.cli --input data/raw/sample_comments.jsonl --out out/demo --platform demo
```

可选：启用 OpenAI-compatible LLM 分析。没有配置密钥时会自动降级为规则分析。

```bash
export SOCIAL_COMMENT_LLM_ENDPOINT="https://api.openai.com/v1"
export SOCIAL_COMMENT_LLM_API_KEY="..."
export SOCIAL_COMMENT_LLM_MODEL="gpt-4o-mini"
PYTHONPATH=src python -m social_comment_agent.cli \
  --input data/raw/sample_comments.jsonl \
  --out out/demo-llm \
  --platform demo \
  --analyzer llm
```

输出：

- `out/demo/pm_insights.md`：给产品经理 agent 的需求洞察报告
- `out/demo/pm_insights.json`：结构化洞察
- `out/demo/agent_tasks/product_manager.json`：产品经理任务包
- `out/demo/agent_tasks/developer.json`：开发任务包
- `out/demo/agent_tasks/tester.json`：测试任务包
- `out/demo/agent_tasks/acceptance.json`：验收任务包
- `out/demo/agent_tasks/dispatch_summary.md`：任务派发摘要

## LLM 配置

项目提供 `.env.example` 模板。复制为本地文件后填写真实密钥，真实 `.env*` 文件已被 `.gitignore` 忽略。

```bash
cp .env.example .env.local
# 编辑 .env.local，填写 SOCIAL_COMMENT_LLM_ENDPOINT / SOCIAL_COMMENT_LLM_API_KEY / SOCIAL_COMMENT_LLM_MODEL
scripts/check_llm_env.sh
```

检查脚本不会打印真实密钥，只会显示是否已配置。未配置完整时，`--analyzer llm` 会安全降级为规则分析。

## 目录扫描 watcher

用于定时扫描授权导出的评论文件。第一次处理新文件时输出 Telegram 友好的摘要，第二次遇到同一文件会静默，适合接 Hermes cron。

```bash
mkdir -p data/inbox
cp data/raw/sample_comments.jsonl data/inbox/sample_comments.jsonl
PYTHONPATH=src python -m social_comment_agent.watcher \
  --inbox data/inbox \
  --archive archive \
  --state .social_comment_watch_state.json \
  --platform demo \
  --dry-run-kanban \
  --kanban-workspace scratch \
  --kanban-tenant social-comment-agent
```

watcher 的 Kanban 行为和一次性 CLI 一样安全：

- `--dry-run-kanban`：只在每个归档目录下生成 `kanban_dry_run/kanban_dry_run.md|json`，不会创建卡片。
- `--dispatch-kanban`：显式创建 Kanban 卡片，并生成 `kanban_dispatch/kanban_dispatch.md|json` 审计报告。
- 不传这两个参数时，只生成 PM 洞察和 agent task 文件。

Hermes cron 可用脚本包装后以 `--no-agent` 静默运行；没有新文件时 watcher 不输出内容。

```bash
# 可选环境变量：SOCIAL_COMMENT_AGENT_INBOX / ARCHIVE / PLATFORM / ANALYZER
# Kanban 模式：none | dry-run | dispatch
export SOCIAL_COMMENT_AGENT_KANBAN_MODE=dry-run
hermes cron create "*/30 * * * *" \
  --name social-comment-watch \
  --script /mnt/d/CodeProj/social-comment-agent/scripts/social_comment_watch.sh \
  --no-agent
```

## Hermes Kanban dry-run / dispatch（可选）

先生成 dry-run，不创建卡片：

```bash
PYTHONPATH=src python -m social_comment_agent.cli \
  --input data/raw/sample_comments.jsonl \
  --out out/demo-kanban \
  --platform demo \
  --dry-run-kanban \
  --kanban-workspace scratch \
  --kanban-tenant social-comment-agent
```

会生成：

- `out/demo-kanban/kanban_tasks.json`：跨角色任务清单
- `out/demo-kanban/kanban_dry_run/kanban_dry_run.md`：可审阅的 `hermes kanban create` 命令
- `out/demo-kanban/kanban_dry_run/kanban_dry_run.json`：结构化 dry-run 结果

确认无误后，再显式派发到 Hermes Kanban：

```bash
PYTHONPATH=src python -m social_comment_agent.cli \
  --input data/raw/sample_comments.jsonl \
  --out out/demo-kanban-dispatch \
  --platform demo \
  --dispatch-kanban \
  --kanban-workspace scratch \
  --kanban-tenant social-comment-agent
```

`--dispatch-kanban` 会实际执行 `hermes kanban create --json` 并额外生成：

- `out/demo-kanban-dispatch/kanban_dispatch/kanban_dispatch.md`：派发审计报告
- `out/demo-kanban-dispatch/kanban_dispatch/kanban_dispatch.json`：结构化执行结果

注意：默认不会创建 Kanban 卡片；只有显式传入 `--dispatch-kanban` 才会派发。

## 流程

1. `collector`：读取评论导出并去重。
2. `analyzer` / `llm_analyzer`：按需求主题聚类或调用 LLM，提取痛点、价值、建议方案和证据评论。
3. `archiver`：归档产品经理报告。
4. `task_router`：按产品经理、开发、测试、验收拆分任务。
5. `watcher`：扫描导出目录，增量生成归档。
6. `cli`：串联完整流水线。

## 后续升级

- 接入平台 API：新增 collector 适配器，但保留合规授权和限流。
- 接入 Hermes Kanban：将 `agent_tasks/*.json` 自动写入看板，分配给不同 profile/agent。
- 定时任务：用 Hermes cron 定期分析导出目录并推送报告给产品经理。
