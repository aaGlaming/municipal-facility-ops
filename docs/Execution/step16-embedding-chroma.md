# Step 16：Embedding 与 Chroma 入库

## 已实现能力

- 通过 `LLM_BASE_URL`、`LLM_API_KEY` 和 `EMBEDDING_MODEL` 配置 OpenAI 兼容 Embedding 服务。
- 按 `EMBEDDING_BATCH_SIZE` 批量生成向量；客户端设置请求超时，并按 `EMBEDDING_MAX_RETRIES` 做指数退避重试。
- 使用每分钟调用窗口限流，避免批量重建时超过 `EMBEDDING_RATE_LIMIT_PER_MINUTE`。
- 使用 `EMBEDDING_CACHE_DIRECTORY` 保存以模型和 Chunk 原文 SHA256 计算的缓存，重复重建命中缓存时不重复调用模型。
- 将 Chunk 文本、向量和文档/版本/区域/页码/标题等 metadata 写入配置的 Chroma collection。
- `embedding_batches` 记录模型、文档版本、Chunk 数、完成数、尝试次数、状态和失败原因；Chunk 保存当前索引状态、批次和模型。
- 提供单文档重建和删除接口；删除后 Chunk 状态回到 `PENDING`。
- Embedding 或 Chroma 写入失败时，先将批次标记为 `FAILED_RETRYABLE`/`FAILED`，不会写入不完整的 Chroma 结果。

## API

- `POST /api/rag/documents/{document_id}/embeddings/rebuild`：重建单文档向量，需要 `document:embed` 权限。
- `DELETE /api/rag/documents/{document_id}/embeddings`：删除单文档向量，需要 `document:embed` 权限。

## 数据库迁移

- 全新数据库的 `infra/mysql/init/001_schema.sql` 已包含 Embedding 字段和 `embedding_batches` 表。
- 已有 MySQL 实例执行 `infra/mysql/init/005_step16_embeddings.sql` 增量迁移。

## 配置

- `EMBEDDING_TIMEOUT_SECONDS=30`
- `EMBEDDING_MAX_RETRIES=3`
- `EMBEDDING_BATCH_SIZE=32`
- `EMBEDDING_RATE_LIMIT_PER_MINUTE=60`
- `EMBEDDING_CACHE_DIRECTORY=.cache/embeddings`
- `CHROMA_COLLECTION_NAME=municipal_facility_ops`

## 验证结果

- `pytest -q`：45 passed
- `python -m ruff check backend/app backend/tests scripts/verify_schema.py`：通过
- `python -m ruff format --check backend/app backend/tests scripts/verify_schema.py`：通过

## 运行边界

当前测试使用 Fake Embedding Provider 和 Fake Chroma Store 验证批量、缓存、失败状态和删除流程；实际模型与 Chroma 连通性需要在配置服务和 API Key 后验证。
