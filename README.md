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

## 真实样本 demo

项目额外提供了一个可提交到 Git 的“授权导出评论”样本：`data/samples/realistic_product_feedback_30.csv`。它包含 30 条中文产品反馈，覆盖小红书、B站、抖音、微博、App Store、社群等来源，用于演示从评论到 PM 洞察、任务拆分、Kanban dry-run 的完整链路。

```bash
cd /mnt/d/CodeProj/social-comment-agent
scripts/demo_realistic.sh
```

默认输出：

- `out/realistic-demo/rules-kanban/pm_insights.md`：规则分析生成的 PM 洞察报告
- `out/realistic-demo/rules-kanban/agent_tasks/*.json`：产品、开发、测试、验收任务包
- `out/realistic-demo/rules-kanban/kanban_dry_run/kanban_dry_run.md`：可审阅的 Hermes Kanban 创建命令，不会真正创建卡片
- `out/realistic-demo/llm-fallback/pm_insights.md`：LLM 模式输出；未配置密钥时会安全降级为规则分析
- `out/realistic-demo/analysis_comparison.md`：规则版与 LLM/fallback 版对比

可选覆盖参数：

```bash
SOCIAL_COMMENT_REALISTIC_OUT=out/my-demo \
SOCIAL_COMMENT_KANBAN_WORKSPACE=/mnt/d/CodeProj/social-comment-agent \
SOCIAL_COMMENT_KANBAN_TENANT=social-comment-agent \
scripts/demo_realistic.sh data/samples/realistic_product_feedback_30.csv
```

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

### Hermes cron 准生产运行

已验证的默认 cron wrapper 放在 `~/.hermes/scripts/social_comment_agent_watch.sh`，它会调用项目内的 `scripts/social_comment_watch.sh`。默认配置：

- 扫描目录：`/mnt/d/CodeProj/social-comment-agent/data/inbox`
- 归档目录：`/mnt/d/CodeProj/social-comment-agent/archive`
- 状态文件：`/mnt/d/CodeProj/social-comment-agent/.social_comment_watch_state.json`
- 分析器：`rules`
- Kanban 模式：`dry-run`
- Kanban workspace：`/mnt/d/CodeProj/social-comment-agent`
- Kanban tenant：`social-comment-agent`

cron job 推荐配置：

```bash
hermes cron create "*/30 * * * *" \
  --name social-comment-agent-watch \
  --script social_comment_agent_watch.sh \
  --no-agent
```

也可以手动验证首跑/二跑行为：

```bash
mkdir -p data/inbox
cp data/samples/realistic_product_feedback_30.csv data/inbox/realistic_product_feedback_30.csv
~/.hermes/scripts/social_comment_agent_watch.sh   # 首跑：输出摘要
~/.hermes/scripts/social_comment_agent_watch.sh   # 二跑：没有新文件则静默
```

环境变量可覆盖默认值：

```bash
SOCIAL_COMMENT_AGENT_KANBAN_MODE=none ~/.hermes/scripts/social_comment_agent_watch.sh
SOCIAL_COMMENT_AGENT_ANALYZER=llm ~/.hermes/scripts/social_comment_agent_watch.sh
```

注意：cron 默认只做 dry-run；只有显式设置 `SOCIAL_COMMENT_AGENT_KANBAN_MODE=dispatch` 才会真实创建 Kanban 卡片。

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
