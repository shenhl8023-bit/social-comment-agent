# 社交平台评论洞察自动化 Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** 做一个本地可运行 MVP：从合规导出的社交平台评论数据中提取产品需求精粹，归档给产品经理 agent，并拆成开发、测试、验收子 agent 任务包。

**Architecture:** 采用 Python CLI 流水线。输入为 JSON/CSV/JSONL 评论导出，避免绕过平台风控或违反 ToS 的登录爬虫；后续可替换 collector 适配官方 API。核心模块：collector、analyzer、archiver、task_router、cli。

**Tech Stack:** Python 3.11 标准库、pytest。

---

### Task 1: 项目骨架与数据模型

**Objective:** 建立包结构和核心 dataclass，支持评论、洞察、任务包的结构化传递。

**Files:**
- Create: `src/social_comment_agent/models.py`
- Create: `pyproject.toml`
- Test: `tests/test_models.py`

**Verification:** `python -m pytest tests/test_models.py -q` 通过。

### Task 2: 输入采集器

**Objective:** 从 JSON/JSONL/CSV 合规导出文件读取评论并规范化字段。

**Files:**
- Create: `src/social_comment_agent/collector.py`
- Test: `tests/test_collector.py`

**Verification:** `python -m pytest tests/test_collector.py -q` 通过。

### Task 3: LLM 可替换需求分析器

**Objective:** 实现无需 API key 的规则分析器，输出需求主题、痛点、功能建议、证据评论；并预留 LLM 适配接口。

**Files:**
- Create: `src/social_comment_agent/analyzer.py`
- Test: `tests/test_analyzer.py`

**Verification:** `python -m pytest tests/test_analyzer.py -q` 通过。

### Task 4: 归档与任务拆分

**Objective:** 将洞察报告归档为 Markdown/JSON，并生成产品经理、开发、测试、验收 agent 的任务文件。

**Files:**
- Create: `src/social_comment_agent/archiver.py`
- Create: `src/social_comment_agent/task_router.py`
- Test: `tests/test_pipeline.py`

**Verification:** `python -m pytest tests/test_pipeline.py -q` 通过。

### Task 5: CLI、样例、验收文档

**Objective:** 提供一条命令跑完整流程，附样例数据和 README 验收步骤。

**Files:**
- Create: `src/social_comment_agent/cli.py`
- Create: `data/raw/sample_comments.jsonl`
- Create: `README.md`

**Verification:** `python -m social_comment_agent.cli --input data/raw/sample_comments.jsonl --out out/demo` 生成报告和任务包。
