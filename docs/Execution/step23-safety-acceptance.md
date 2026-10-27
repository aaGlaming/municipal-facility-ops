# Step23：安全作业与维修验收 Agent

## 实现内容

- `SafetyAgent` 识别带电、燃气、高空、封路/交通和开挖风险，生成风险标签、断电/隔离措施、PPE、围挡、交通防护和禁止动作清单。
- 低风险场景可以输出通用安全控制建议；高风险场景返回 `requires_confirmation=true` 和 `safe_to_proceed=false`，不会自动批准现场动作。
- `AcceptanceAgent` 根据工单状态、处理说明、维修证据、验收检查项和缺陷判断 `ACCEPTED`、`CONDITIONAL_ACCEPTANCE` 或 `REWORK_REQUIRED`。
- 证据不足、工单未完成、检查项未完成或存在缺陷时不会建议直接关闭工单。
- 最终验收、返工和关闭仍通过权限、状态机、人工确认和 Step19 工具网关执行。

## 结构化接口

- `SafetyAssessmentRequest` / `SafetyAssessmentResult`
- `AcceptanceAssessmentRequest` / `AcceptanceAssessmentResult`

## Gold Set 评测

- 数据集：`evaluation/datasets/safety_acceptance_gold.jsonl`。
- 命令：`$env:PYTHONPATH='backend'; python scripts/evaluate_safety_acceptance.py`
- 当前结果：风险准确率 `1.0`，人工确认准确率 `1.0`。

## 验证

- Step23 定向测试：4 passed
- 全量测试：72 passed
