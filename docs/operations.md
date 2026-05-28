# Social Comment Agent Operations Guide

本文档面向准生产使用：把平台后台、官方 API、数据工具或人工整理出的授权评论导出文件放进 inbox，由 watcher 增量生成 PM 洞察、agent 任务包、Kanban dry-run、趋势报告和历史洞察知识库。

## 1. 运行边界

- 只处理用户授权、平台后台、官方 API 或人工导出的 `.csv/.json/.jsonl` 文件。
- 不绕过登录、验证码、反爬、风控、限流或平台权限控制。
- 默认不真实创建 Kanban 卡片；只有显式开启 dispatch 才会创建。
- 默认不打印密钥；LLM 环境变量只在本机配置，不提交到 Git。

## 2. 目录约定

默认项目根目录：

```bash
/mnt/d/CodeProj/social-comment-agent
```

常用目录：

- `data/samples/`：可提交的演示样本。
- `data/inbox/`：watcher 扫描入口，运行时目录，已被 `.gitignore` 忽略。
- `archive/`：每次处理后的归档目录，运行时目录，已被 `.gitignore` 忽略。
- `knowledge_base/`：历史 PM 洞察索引，运行时目录，已被 `.gitignore` 忽略。
- `.social_comment_watch_state.json`：已处理文件状态，运行时文件，已被 `.gitignore` 忽略。
- `out/`：一次性 demo 输出，运行时目录，已被 `.gitignore` 忽略。

## 3. 新评论导入流程

先把导出文件放到 inbox：

```bash
cd /mnt/d/CodeProj/social-comment-agent
mkdir -p data/inbox
cp data/samples/realistic_product_feedback_30.csv data/inbox/realistic_product_feedback_30.csv
```

建议先做导入预检：

```bash
PYTHONPATH=src python -m social_comment_agent.import_wizard \
  data/inbox/realistic_product_feedback_30.csv \
  --platform authorized_export
```

如果是平台后台导出，可以先查看内置模板：

```bash
PYTHONPATH=src python -m social_comment_agent.import_wizard --list-platform-templates
```

## 4. 手动执行 watcher

安全 dry-run：

```bash
PYTHONPATH=src python -m social_comment_agent.watcher \
  --inbox data/inbox \
  --archive archive \
  --state .social_comment_watch_state.json \
  --platform authorized_export \
  --trend \
  --trend-bucket week \
  --dry-run-kanban \
  --kanban-workspace /mnt/d/CodeProj/social-comment-agent \
  --kanban-tenant social-comment-agent \
  --knowledge-base knowledge_base
```

首跑有新文件时会输出 Telegram 友好的摘要；同一文件二跑不会重复输出。

## 5. Hermes cron 运行

项目内 wrapper：

```bash
scripts/social_comment_watch.sh
```

Hermes cron 使用的 wrapper 可放在：

```bash
~/.hermes/scripts/social_comment_agent_watch.sh
```

推荐 cron：

```bash
hermes cron create "*/30 * * * *" \
  --name social-comment-agent-watch \
  --script social_comment_agent_watch.sh \
  --no-agent
```

`--no-agent` 的语义：脚本 stdout 非空才发送消息；没有新文件时 stdout 为空，保持静默。

## 6. 环境变量开关

常用覆盖项：

```bash
SOCIAL_COMMENT_AGENT_ROOT=/mnt/d/CodeProj/social-comment-agent
SOCIAL_COMMENT_AGENT_INBOX=/mnt/d/CodeProj/social-comment-agent/data/inbox
SOCIAL_COMMENT_AGENT_ARCHIVE=/mnt/d/CodeProj/social-comment-agent/archive
SOCIAL_COMMENT_AGENT_STATE=/mnt/d/CodeProj/social-comment-agent/.social_comment_watch_state.json
SOCIAL_COMMENT_AGENT_PLATFORM=authorized_export
SOCIAL_COMMENT_AGENT_ANALYZER=rules
SOCIAL_COMMENT_AGENT_KANBAN_MODE=none
SOCIAL_COMMENT_AGENT_KANBAN_WORKSPACE=/mnt/d/CodeProj/social-comment-agent
SOCIAL_COMMENT_AGENT_KANBAN_TENANT=social-comment-agent
SOCIAL_COMMENT_AGENT_TREND_MODE=week
SOCIAL_COMMENT_AGENT_KNOWLEDGE_BASE=/mnt/d/CodeProj/social-comment-agent/knowledge_base
```

Kanban 模式：

- `none`：不生成 Kanban 命令。
- `dry-run`：只生成可审阅命令，不创建卡片。
- `dispatch`：真实创建 Hermes Kanban 卡片，并写审计报告。

趋势模式：

- `none`：不生成趋势报告。
- `week`：按周生成趋势报告。
- `month`：按月生成趋势报告。

## 7. 查看输出

处理完成后，每个导出文件会有一个归档目录，形如：

```text
archive/20260526T223916Z/realistic_product_feedback_30/
```

重点文件：

- `pm_insights.md`：PM 可读需求洞察。
- `pm_insights.json`：结构化洞察。
- `agent_tasks/product_manager.json`：产品经理任务包。
- `agent_tasks/developer.json`：开发任务包。
- `agent_tasks/tester.json`：测试任务包。
- `agent_tasks/acceptance.json`：验收任务包。
- `agent_tasks/dispatch_summary.md`：跨角色任务摘要。
- `kanban_dry_run/kanban_dry_run.md`：Hermes Kanban 创建命令预览。
- `trends/trend_report.md`：周/月趋势报告。

知识库输出：

- `knowledge_base/knowledge_base.md`：PM 可读历史洞察索引。
- `knowledge_base/knowledge_base.json`：结构化检索索引。

检索历史洞察：

```bash
PYTHONPATH=src python -m social_comment_agent.cli knowledge-base search "导出 报表" \
  --index knowledge_base/knowledge_base.json \
  --limit 5
```

## 8. 排障

### 没有输出

可能原因：

- inbox 没有 `.csv/.json/.jsonl` 文件。
- 文件已经处理过，状态文件记录了同一 fingerprint。
- cron `--no-agent` 模式下脚本 stdout 为空会静默，这是正常行为。

处理：

```bash
rm .social_comment_watch_state.json
PYTHONPATH=src python -m social_comment_agent.watcher --inbox data/inbox --archive archive --state .social_comment_watch_state.json
```

### 导入字段识别错误

先跑 import wizard：

```bash
PYTHONPATH=src python -m social_comment_agent.import_wizard path/to/export.csv --platform-template xiaohongshu
```

根据预检输出调整导出字段或选择合适平台模板。

### Kanban 卡片误创建风险

默认使用：

```bash
SOCIAL_COMMENT_AGENT_KANBAN_MODE=none
```

只有明确确认后才切到：

```bash
SOCIAL_COMMENT_AGENT_KANBAN_MODE=dispatch
```

### LLM 分析没有生效

检查本地环境变量，不要打印真实密钥：

```bash
scripts/check_llm_env.sh
```

未配置完整时，`--analyzer llm` 会自动降级为规则分析。

## 9. 发布前检查

提交前执行：

```bash
PYTHONPATH=src python -m compileall -q src tests
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m social_comment_agent.cli --input data/samples/realistic_product_feedback_30.csv --out out/ops-smoke --platform authorized_export --dry-run-kanban --knowledge-base knowledge_base
PYTHONPATH=src python -m social_comment_agent.cli knowledge-base search "导出 报表" --index knowledge_base/knowledge_base.json --limit 3
```

确认：

- 测试通过。
- `out/ops-smoke/pm_insights.md` 存在。
- `out/ops-smoke/kanban_dry_run/kanban_dry_run.md` 存在。
- `knowledge_base/knowledge_base.md|json` 存在。
- 搜索命令能返回相关历史洞察。
