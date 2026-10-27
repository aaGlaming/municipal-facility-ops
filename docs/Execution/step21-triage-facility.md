# Step21：问题分诊与设施识别 Agent

## 实现内容

- `backend/app/agents/triage_agent.py` 提供只读 `TriageAgent`，不会创建或修改设施台账。
- `TRIAGE_PROMPT` 明确要求先分类、再匹配候选，并在低置信度时请求人工确认。
- 支持问题类别识别：道路坑洼、路灯、交通信号、排水、垃圾桶、人行道和其他问题。
- 根据危险、事故、通行影响和设施类型计算 P1-P4 优先级。
- 结合区域、设施类型、地址/名称关键词和坐标匹配设施候选，返回置信度和匹配理由。
- 低于 `0.75` 的候选不会写入 `selected_facility_id`，并返回缺失字段和人工确认信号。
- 查询近 24 小时同区域、同类别的相似报修，返回重复报修 ID、相似度和当前状态。

## 结构化输出

`TriageResult` 包含 `category`、`priority`、`confidence`、`candidates`、`selected_facility_id`、`requires_confirmation`、`duplicate_reports`、`rationale` 和 `evidence`。

## Gold Set 评测

- 数据集：`evaluation/datasets/triage_gold.jsonl`，6 条可重复样例。
- 命令：`$env:PYTHONPATH='backend'; python scripts/evaluate_triage.py`
- 当前结果：类别准确率 `1.0`，优先级准确率 `1.0`。

## 验证

- Step21 定向测试：3 passed
- 全量测试：64 passed
