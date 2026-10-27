# Step 29：建立评测数据集与基准

## 完成内容

- 建立统一配置 `evaluation/benchmark_config.json`，固定 benchmark/dataset 版本、随机 seed、规则模型版本、Prompt 版本、RAG 参数和指标阈值。
- 建立 7 组 Gold Set：分诊、设施匹配、SLA/调度、工单状态流转、RAG 检索、高风险作业和安全验收。
- 数据集按 simple、medium、complex、very_complex 分层，样例均使用稳定 ID，重复 ID 和低于最低样本数会使基线脚本直接失败。
- 新增 `scripts/evaluate_benchmark.py`，统一校验数据集结构并运行已有分诊、SLA、安全评测，同时计算状态流转、设施匹配规则和评测 fixture 完备度。
- 输出 `evaluation/reports/step29-baseline.json`，记录版本、参数、模型、各数据集样本数和可用指标。
- 设施台账真实 ID 命中率与 RAG Hit Rate/MRR 暂不填充，明确留给 Step30/31 的固定数据库与 Chroma fixture，避免基线结果失真。

## 基线命令与结果

```powershell
$env:PYTHONPATH='backend'; python scripts/evaluate_benchmark.py
```

- 分诊类别/优先级：1.0 / 1.0。
- SLA/调度优先级/SLA 分钟：1.0 / 1.0。
- 状态流转准确率：1.0。
- 高风险与安全验收风险/确认准确率：1.0。
- 设施匹配类别/确认准确率：1.0 / 1.0；设施 ID 命中率等待固定设施台账 fixture。
- RAG 数据集 fixture 完备度：1.0；真实召回指标等待 Step30。

## 校验记录

- 统一基线脚本：通过并生成报告。
- `python -m ruff check backend/app backend/tests scripts`：通过。
- `python -m ruff format --check backend/app backend/tests scripts`：通过。
- `pytest -q backend/tests`：80 passed。
- `git diff --check`：通过。
