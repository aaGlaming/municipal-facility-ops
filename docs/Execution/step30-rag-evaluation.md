# Step 30：执行 RAG 评测

## 评测方法

- 使用 `evaluation/datasets/rag_retrieval_gold.jsonl` 的 5 条分层样例，固定 `step30-v1` fixture、SQLite 数据库和 `rag-fixture-v1` Embedding/Chroma 替身；不连接外部文档 MCP。
- 每条样例建立已解析、已索引、有页码和 metadata 的文档 Chunk，并通过假向量库固定相关文档排序，评测逻辑仍调用生产 `search_documents`。
- 计算 Recall@1、Hit Rate@3/5、MRR、来源正确率、Chunk 可定位率、metadata 过滤正确率和过期文档拦截率。
- 失败归因分为 `missing_recall`、`filter_leak`、`wrong_source` 和 `chunk_unlocatable`，报告同时记录改进建议。

## 执行命令

```powershell
$env:PYTHONPATH='backend'; python scripts/evaluate_rag.py
```

报告写入 `evaluation/reports/step30-rag-baseline.json`。

## 基线结果

| 指标 | 结果 |
| --- | ---: |
| Recall@1 | 1.0000 |
| Hit Rate@3 | 1.0000 |
| Hit Rate@5 | 1.0000 |
| MRR | 1.0000 |
| 来源正确率 | 1.0000 |
| Chunk 可定位率 | 1.0000 |
| metadata 过滤正确率 | 1.0000 |
| 过期文档拦截率 | 1.0000 |

当前报告验证的是检索服务逻辑和过滤/排序契约。Step30 后续接入真实 Chroma 服务时，需保留同一 Gold Set 并比较向量距离排序；失败样例必须回写报告，不得用外部 MCP 资料替换固定数据。

## 校验记录

- `python scripts/evaluate_rag.py`：通过并生成报告。
- `pytest -q backend/tests`：80 passed。
- Ruff 检查和格式检查：通过。
- `git diff --check`：通过。
