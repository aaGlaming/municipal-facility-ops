# Step 15：文本清洗与 Chunk 预览

## 已实现能力

- 清洗 Unicode 兼容字符、零宽字符、不可见控制字符、重复空白和无意义页码行。
- 根据跨分段重复行识别并移除常见页眉/页脚，保留 Step14 的原始 `document_parts` 不变。
- 按段落、标题和表格分段生成 Chunk；超长分段按目标字符边界切分，并保留重叠窗口。
- 默认目标 800 tokens、重叠 120 tokens；参数可在预览和重新生成时调整，范围受到服务端限制。
- 保存 `chunk_id`、`document_id`、`chunk_index`、页码、标题、来源分段、原文偏移、token 估算和清洗版本。
- `GET /api/rag/documents/{document_id}/chunks/preview` 提供不落库的独立预览。
- `POST /api/rag/documents/{document_id}/chunks/regenerate` 删除旧 Chunk 并按新参数重新生成入库。
- `GET /api/rag/documents/{document_id}/chunks` 查看当前持久化 Chunk。

## 数据库迁移

新增 `document_chunks` 表；已有 MySQL 实例使用 `infra/mysql/init/004_step15_chunks.sql` 增量迁移。Step16 Embedding 尚未开始，Chunk 仍只保存在 MySQL。

## 配置

- `RAG_CHUNK_TARGET_TOKENS=800`
- `RAG_CHUNK_OVERLAP_TOKENS=120`

## 验证结果

- `python -m pytest -q`：42 passed
- `python -m ruff check backend scripts`：通过
- `python -m ruff format --check backend scripts`：通过

Step 16 尚未开始。
