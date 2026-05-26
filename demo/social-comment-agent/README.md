# Social Comment Agent Demo Package

这个目录保留一组可提交的端到端演示产物，用来快速展示“授权评论导出 → PM 洞察 → 子 Agent 任务 → Kanban dry-run → PM 洞察知识库”的闭环。

## 文件说明

- `sample_input.csv`：授权导出风格的评论样本。
- `sample_pm_insights.md`：PM 可读需求洞察报告。
- `sample_agent_tasks.md`：产品、开发、测试、验收任务拆分摘要。
- `sample_kanban_dry_run.md`：不会真实创建卡片的 Hermes Kanban 命令预览。
- `sample_knowledge_base.md`：从归档洞察构建的历史 PM 知识库样例。
- `run/`：生成上述产物时的完整结构化输出。
- `knowledge_base/`：结构化知识库输出。

## 重新生成

```bash
cd /mnt/d/CodeProj/social-comment-agent
rm -rf demo/social-comment-agent
mkdir -p demo/social-comment-agent
cp data/samples/realistic_product_feedback_30.csv demo/social-comment-agent/sample_input.csv
PYTHONPATH=src python -m social_comment_agent.cli \
  --input demo/social-comment-agent/sample_input.csv \
  --out demo/social-comment-agent/run \
  --platform authorized_export \
  --dry-run-kanban \
  --kanban-workspace /mnt/d/CodeProj/social-comment-agent \
  --kanban-tenant social-comment-agent \
  --knowledge-base demo/social-comment-agent/knowledge_base
cp demo/social-comment-agent/run/pm_insights.md demo/social-comment-agent/sample_pm_insights.md
cp demo/social-comment-agent/run/agent_tasks/dispatch_summary.md demo/social-comment-agent/sample_agent_tasks.md
cp demo/social-comment-agent/run/kanban_dry_run/kanban_dry_run.md demo/social-comment-agent/sample_kanban_dry_run.md
cp demo/social-comment-agent/knowledge_base/knowledge_base.md demo/social-comment-agent/sample_knowledge_base.md
```
