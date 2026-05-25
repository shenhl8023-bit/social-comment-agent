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

输出：

- `out/demo/pm_insights.md`：给产品经理 agent 的需求洞察报告
- `out/demo/pm_insights.json`：结构化洞察
- `out/demo/agent_tasks/product_manager.json`：产品经理任务包
- `out/demo/agent_tasks/developer.json`：开发任务包
- `out/demo/agent_tasks/tester.json`：测试任务包
- `out/demo/agent_tasks/acceptance.json`：验收任务包
- `out/demo/agent_tasks/dispatch_summary.md`：任务派发摘要

## 流程

1. `collector`：读取评论导出并去重。
2. `analyzer`：按需求主题聚类，提取痛点、价值、建议方案和证据评论。
3. `archiver`：归档产品经理报告。
4. `task_router`：按产品经理、开发、测试、验收拆分任务。
5. `cli`：串联完整流水线。

## 后续升级

- 接入真实 LLM：替换 `DemandAnalyzer.analyze()` 内部逻辑，保持 `AnalysisReport` 输出结构不变。
- 接入平台 API：新增 collector 适配器，但保留合规授权和限流。
- 接入 Hermes Kanban：将 `agent_tasks/*.json` 自动写入看板，分配给不同 profile/agent。
- 定时任务：用 Hermes cron 定期分析导出目录并推送报告给产品经理。
