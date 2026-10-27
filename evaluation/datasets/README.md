# Evaluation datasets

放置检索 Hit Rate/MRR 和 Agent 工具调用正确性评测样本。公开数据只能作为事实样本，合成样本必须标注来源。

Step29 数据集由 `../benchmark_config.json` 固定版本、seed、Prompt/模型版本、参数和指标阈值。当前覆盖：

- 分诊：`triage_gold.jsonl`
- 设施匹配：`facility_matching_gold.jsonl`
- SLA/调度：`scheduling_gold.jsonl`
- 工单状态流转：`state_transition_gold.jsonl`
- RAG 检索：`rag_retrieval_gold.jsonl`
- 高风险作业：`high_risk_gold.jsonl`、`safety_acceptance_gold.jsonl`

运行统一基线：`$env:PYTHONPATH='backend'; python scripts/evaluate_benchmark.py`。输出写入 `evaluation/reports/step29-baseline.json`；数据库设施台账和实际 RAG 召回在 Step30/31 接入，避免在没有固定 fixture 时伪造命中率。
