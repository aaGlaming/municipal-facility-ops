# Step 17：RAG 检索与原文展示

## 已实现能力

- 对查询做确定性改写和字段提取，识别设施类型、区域、文档版本和生效日期；请求显式过滤优先于查询中识别出的字段。
- 组合 Chroma 向量召回和 MySQL 关键词召回，以 Chunk ID 去重并合并候选；默认返回 Top-K 为 5，允许调用方调整到 1～50。
- 支持区域权限、设施类型、区域、版本和当前生效日期过滤；解析失败、软删除、未索引和过期文档不会进入结果。
- 支持可选的确定性轻量 rerank，对标题命中的候选进行加权，不依赖额外模型调用。
- 返回文档名、页码、Chunk ID、相似度、文档版本、来源、区域、设施类型和原文片段。
- 无召回时返回 `NO_RECALL` 和原因；向量服务不可用但关键词有结果时返回 `PARTIAL` 与 warning；两类召回都不可用时返回 `RETRIEVAL_UNAVAILABLE`。
- 提供检索调试接口，返回关键词/向量/合并/返回数量、Embedding 模型、失败提示和耗时，不返回密钥或原始凭据。

## API

- `POST /api/rag/search`：执行混合检索，需要 `document:read` 权限。
- `POST /api/rag/search/debug`：执行检索并返回调试统计，需要 `document:read` 权限。

请求示例：

```json
{
  "query": "street_light repair DISTRICT-01 v2",
  "top_k": 5,
  "rerank": true
}
```

响应中的 `items` 包含 `document_name`、`page_number`、`chunk_id`、`similarity`、`snippet` 和 `metadata`，可直接用于原文定位展示。

## 验证结果

- `pytest -q`：48 passed
- `python -m ruff check backend/app backend/tests`：通过
- `python -m ruff format --check backend/app backend/tests`：通过

## 运行边界

实际向量召回需要已运行的 Chroma、可用的 OpenAI 兼容 Embedding 端点和完成 Step16 入库的 Chunk；关键词召回可在向量服务暂不可用时作为降级路径。
