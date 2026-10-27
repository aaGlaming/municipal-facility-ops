# Step22：SLA、巡检计划与工单调度 Agent

## 实现内容

- `backend/app/agents/scheduling_agent.py` 提供 `SchedulingAgent`、`SlaAgent` 和 `DispatchAgent`。
- SLA 使用确定性规则计算优先级、首次响应截止时间和解决截止时间，并解释公共安全、高关键性设施和重复报修升级原因。
- 巡检计划根据优先级生成建议时间、截止时间和区域内可用人员候选；P1 和公共安全巡检进入人工确认。
- 工单调度根据区域、人员容量、活动工单、巡检时间窗口和重复派工检查候选；冲突候选不会被标记为可用。
- P1、公共安全、重复派工、无可用人员和容量/时间冲突进入确认或阻断分支。
- 调度 Agent 只生成可审计计划，不直接修改工单或巡检状态；实际变更必须通过 Step19 工具网关。

## 结构化接口

- `SlaPlanRequest` / `SlaPlanResult`
- `InspectionPlanRequest` / `InspectionPlanResult`
- `DispatchPlanRequest` / `DispatchPlanResult`

## Gold Set 评测

- 数据集：`evaluation/datasets/scheduling_gold.jsonl`。
- 命令：`$env:PYTHONPATH='backend'; python scripts/evaluate_scheduling.py`
- 当前结果：优先级准确率 `1.0`，SLA 分钟准确率 `1.0`。

## 验证

- Step22 定向测试：4 passed
- 全量测试：68 passed
