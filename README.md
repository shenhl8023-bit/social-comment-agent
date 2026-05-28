# Social Comment Agent

本项目是一个“社交平台评论区 → 需求洞察 → 产品经理归档 → 子 Agent 任务派发”的本地自动化 MVP。

## 合规边界

- 默认读取平台后台、官方 API、数据工具或人工导出的 `.jsonl/.json/.csv` 评论文件。
- 不内置绕过登录、验证码、反爬、风控的爬虫。
- 后续如果接入抖音/小红书/B站等平台，应优先用官方开放平台或用户授权导出。

## 一键运行

```bash
cd /mnt/d/CodeProj/social-comment-agent
PYTHONPATH=src python -m social_comment_agent --input data/raw/sample_comments.jsonl --out out/demo --platform demo
```

可选：启用 OpenAI-compatible LLM 分析。没有配置密钥时会自动降级为规则分析。

```bash
export SOCIAL_COMMENT_LLM_ENDPOINT="https://api.openai.com/v1"
export SOCIAL_COMMENT_LLM_API_KEY="..."
export SOCIAL_COMMENT_LLM_MODEL="gpt-4o-mini"
PYTHONPATH=src python -m social_comment_agent \
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

## 导入预检

把平台后台、官方 API 或数据工具导出的文件放进 watcher 前，建议先运行导入预检，确认字段是否能被识别。

```bash
PYTHONPATH=src python -m social_comment_agent.import_wizard \
  data/samples/realistic_product_feedback_30.csv \
  --platform authorized_export
```

也可以应用内置平台模板，让预检按常见导出字段优先识别：

```bash
PYTHONPATH=src python -m social_comment_agent.import_wizard --list-platform-templates

PYTHONPATH=src python -m social_comment_agent.import_wizard \
  path/to/xiaohongshu_export.csv \
  --platform-template xiaohongshu
```

当前内置模板：

- `xiaohongshu`：小红书创作者/蒲公英/运营后台授权导出
- `bilibili`：B站创作中心或授权导出
- `douyin`：抖音创作者服务中心或授权导出
- `weibo`：微博创作者/企业账号后台或授权导出
- `app_store`：App Store Connect / 应用商店评价导出
- `wechat_group`：微信/企业微信/社群反馈整理表

输出会包含：

- 文件格式和总行数
- 可识别评论数、去重后评论数
- 应用的平台模板，以及识别到的 `text/author/created_at/post_id/comment_id/platform/likes/rating/url` 等字段
- 缺少评论内容、重复评论、缺少平台/ID、模板推荐字段缺失等风险提示
- 是否建议直接放入 `data/inbox/`

当前支持 `.csv/.json/.jsonl`，并兼容常见字段别名，例如 `text/content/comment/body/message/评论/内容/评论内容/消息内容/评价内容`。

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
  --trend \
  --trend-bucket week \
  --dry-run-kanban \
  --kanban-workspace scratch \
  --kanban-tenant social-comment-agent \
  --knowledge-base knowledge_base
```

watcher 的 Kanban 行为和一次性 CLI 一样安全：

- `--dry-run-kanban`：只在每个归档目录下生成 `kanban_dry_run/kanban_dry_run.md|json`，不会创建卡片。
- `--dispatch-kanban`：显式创建 Kanban 卡片，并生成 `kanban_dispatch/kanban_dispatch.md|json` 审计报告。
- 不传这两个参数时，只生成 PM 洞察和 agent task 文件。
- `--trend --trend-bucket week|month`：在每个归档目录下额外生成 `trends/trend_report.md|json`，摘要里会附带当前周期、升温/降温主题和趋势报告路径。
- `--knowledge-base knowledge_base`：扫描归档目录内的历史 `pm_insights.json`，生成可检索的 PM 洞察知识库 `knowledge_base/knowledge_base.md|json`，摘要里会附带知识库路径。

### Hermes cron 准生产运行

已验证的默认 cron wrapper 放在 `~/.hermes/scripts/social_comment_agent_watch.sh`，它会调用项目内的 `scripts/social_comment_watch.sh`。默认配置：

- 扫描目录：`/mnt/d/CodeProj/social-comment-agent/data/inbox`
- 归档目录：`/mnt/d/CodeProj/social-comment-agent/archive`
- 状态文件：`/mnt/d/CodeProj/social-comment-agent/.social_comment_watch_state.json`
- 分析器：`rules`
- Kanban 模式：`none`
- 趋势分析：默认开启周趋势；设置 `SOCIAL_COMMENT_AGENT_TREND_MODE=none` 可关闭，或设置为 `month` 改为月趋势
- 知识库：默认生成到 `/mnt/d/CodeProj/social-comment-agent/knowledge_base`；清空 `SOCIAL_COMMENT_AGENT_KNOWLEDGE_BASE` 可关闭索引生成
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
SOCIAL_COMMENT_AGENT_TREND_MODE=week ~/.hermes/scripts/social_comment_agent_watch.sh
SOCIAL_COMMENT_AGENT_KNOWLEDGE_BASE=/mnt/d/CodeProj/social-comment-agent/knowledge_base ~/.hermes/scripts/social_comment_agent_watch.sh
```

注意：cron 默认不生成 Kanban dry-run，也不会真实创建 Kanban 卡片；只有显式设置 `SOCIAL_COMMENT_AGENT_KANBAN_MODE=dry-run` 才会生成可审阅命令，设置 `dispatch` 才会真实创建卡片。趋势分析和知识库默认开启，方便自动摘要和历史洞察检索；如需完全静默的轻量扫描，可把 `SOCIAL_COMMENT_AGENT_TREND_MODE=none` 并清空 `SOCIAL_COMMENT_AGENT_KNOWLEDGE_BASE`。

## PM 洞察知识库

知识库会从历史归档中的 `pm_insights.json` 提取洞察标题、优先级、问题、用户价值、建议方案和证据评论，生成本地 Markdown/JSON 索引，便于后续需求评审和子 agent 分工复用。

一次性 CLI 生成：

```bash
PYTHONPATH=src python -m social_comment_agent \
  --input data/raw/sample_comments.jsonl \
  --out archive/manual-run \
  --platform demo \
  --knowledge-base knowledge_base
```

也可以在 watcher 扫描时传入 `--knowledge-base knowledge_base`，每次处理新文件后自动重建索引。

输出：

- `knowledge_base/knowledge_base.md`：PM 可读历史洞察索引
- `knowledge_base/knowledge_base.json`：结构化检索索引；代码内可用 `search_knowledge_base(path, query)` 做关键词检索

CLI 检索历史洞察：

```bash
PYTHONPATH=src python -m social_comment_agent knowledge-base search "导出 报表" \
  --index knowledge_base/knowledge_base.json \
  --limit 5
```

输出会按优先级和关键词匹配数排序，包含标题、优先级、匹配词、问题/建议、证据评论和来源报告路径。

## Hermes Kanban dry-run / dispatch（可选）

先生成 dry-run，不创建卡片：

```bash
PYTHONPATH=src python -m social_comment_agent \
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
PYTHONPATH=src python -m social_comment_agent \
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

## 需求趋势分析

当评论样本覆盖多个周期时，可以生成按周/按月的主题趋势报告，帮助 PM 识别“本周升温/降温”的用户问题。

```bash
PYTHONPATH=src python -m social_comment_agent.trends \
  --input data/samples/historical_product_feedback_2weeks.csv \
  --out out/trends-weekly \
  --platform authorized_export \
  --bucket week

PYTHONPATH=src python -m social_comment_agent.trends \
  --input data/samples/historical_product_feedback_2weeks.csv \
  --out out/trends-monthly \
  --platform authorized_export \
  --bucket month
```

输出：

- `out/trends-weekly/trend_report.md`：PM 可读趋势报告，包含当前周期、上一周期、主题增减和代表评论
- `out/trends-weekly/trend_report.json`：结构化趋势数据，便于后续进入日报/周报或 Kanban

样例数据：`data/samples/historical_product_feedback_2weeks.csv` 是两周授权导出风格评论，用于验证趋势链路。

## 准生产运行

详细操作手册见 `docs/operations.md`，覆盖 inbox 目录约定、Hermes cron、环境变量、输出查看、知识库检索和排障。

## 可交付 demo 包

项目保留了一组可提交的端到端演示产物：`demo/social-comment-agent/`。

核心文件：

- `demo/social-comment-agent/sample_input.csv`：授权导出风格评论样本
- `demo/social-comment-agent/sample_pm_insights.md`：PM 洞察报告样例
- `demo/social-comment-agent/sample_agent_tasks.md`：子 Agent 任务拆分样例
- `demo/social-comment-agent/sample_kanban_dry_run.md`：Kanban dry-run 命令样例
- `demo/social-comment-agent/sample_knowledge_base.md`：历史 PM 洞察知识库样例

## 流程

1. `import_wizard`：预检授权导出的 `.csv/.json/.jsonl`，可套用平台模板确认字段映射、跳过行、重复评论和推荐字段缺失。
2. `collector`：读取评论导出并去重。
3. `analyzer` / `llm_analyzer`：按需求主题聚类或调用 LLM，提取痛点、价值、建议方案和证据评论。
4. `archiver`：归档产品经理报告。
5. `task_router`：按产品经理、开发、测试、验收拆分任务。
6. `watcher`：扫描导出目录，增量生成归档。
7. `cli`：串联完整流水线。

## 后续升级

- 接入平台 API：新增 collector 适配器，但继续坚持官方 API、授权导出和限流边界。
- 在真实评论样本稳定后，把 `SOCIAL_COMMENT_AGENT_KANBAN_MODE` 从 `none` 调整为 `dry-run`，人工确认任务质量后再考虑 `dispatch`。
- 增加面向具体平台/业务的字段模板和术语词典，提高真实导出文件的识别率和主题分类质量。
