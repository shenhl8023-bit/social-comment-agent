# Sample comment exports

这里放可提交到 Git 的授权导出样本，用于本地演示、CI 验证和端到端调试。`data/inbox/` 是运行时目录，会被 cron watcher 消费并被 `.gitignore` 忽略；不要把长期样本放进 `data/inbox/`。

## realistic_product_feedback_30.csv

30 条贴近真实业务的中文评论样本，覆盖小红书、B站、抖音、微博、App Store、社群反馈等来源。主题包括：

- 评论导入和平台适配
- 报告质量、证据评论、PRD/任务生成
- 性能卡顿、闪退和大文件导入
- 价格、退款、订阅和发票
- 客服响应、充值额度、信任问题
- 协作、状态流转、飞书/企微推送
- 数据保留、脱敏、趋势分析

运行：

```bash
scripts/demo_realistic.sh
```
