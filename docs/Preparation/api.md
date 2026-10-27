# FastAPI 基础 API

服务默认地址：`http://127.0.0.1:8000`

## 请求上下文

- 可选请求头：`X-Request-Id`、`X-Trace-Id`。
- 服务会在响应中回传这两个请求头。
- 未提供或超过 128 个字符的值会被替换为服务端生成的 UUID。

## 健康检查

### `GET /health`

进程存活检查，不访问 MySQL、Chroma 或模型服务。

```json
{
  "status": "ok",
  "trace_id": "..."
}
```

### `GET /ready`

检查 MySQL、Chroma 和 LLM。依赖不完整时返回 HTTP 503：

```json
{
  "status": "not_ready",
  "checks": {"mysql": "ok", "chroma": "ok", "llm": "not_configured"},
  "code": "DEPENDENCY_NOT_READY",
  "message": "一个或多个依赖服务不可用",
  "trace_id": "...",
  "retryable": true
}
```

## 统一错误

```json
{
  "code": "VALIDATION_ERROR",
  "message": "请求参数校验失败",
  "trace_id": "...",
  "retryable": false
}
```

完整 OpenAPI 描述由 FastAPI 在 `/openapi.json` 提供。

## 设施

- `GET /api/facilities`：分页、类型、状态、区域、来源和关键词筛选。
- `GET /api/facilities/{facility_id}`：设施详情和位置。
- `GET /api/facilities/{facility_id}/events`：设施关联问题历史。
- `GET /api/facilities/nearby`：按 WGS84 坐标、半径和类型查询附近设施。

## 问题上报

- `POST /api/reports`：创建内部问题，支持 `idempotency_key` 和 `external_id`。
- `GET /api/reports`、`GET /api/reports/{report_id}`：按区域、状态、分类和来源查询。
- `PATCH /api/reports/{report_id}/status`：执行受控状态变更。
- `POST /api/reports/import/public`：导入公开事件，记录为 `source_type=public`。

## 巡检和工单

- `POST/GET /api/inspections`：创建和查询巡检任务。
- `PATCH /api/inspections/{task_id}/assign`：分配巡检人员。
- `PATCH /api/inspections/{task_id}/status`：开始、延期、恢复或完成巡检。
- `POST/GET /api/work-orders`：创建和查询工单。
- `POST /api/work-orders/{work_order_id}/status`：执行状态机流转。
- `POST /api/work-orders/{work_order_id}/acceptance`：提交验收结果和证据。
- `POST /api/work-orders/escalate-overdue`：将超 SLA 未终态工单升级。

## RAG 文档

- `POST /api/rag/documents`：上传并解析 PDF、DOCX、Markdown、TXT 或 HTML 文档。
- `GET /api/rag/documents/{document_id}`：查看文档元数据、解析状态和原文分段。

上传接口需要 `document:upload` 权限，查看接口需要 `document:read` 权限；解析失败会保留失败文档记录并返回 `DOCUMENT_PARSE_FAILED`。

## Chunk 预览

- `GET /api/rag/documents/{document_id}/chunks/preview`：按参数预览清洗和切块结果，不修改数据库。
- `POST /api/rag/documents/{document_id}/chunks/regenerate`：按新目标/重叠参数重新生成并持久化 Chunk，需要 `document:chunk`。
- `GET /api/rag/documents/{document_id}/chunks`：查看当前持久化 Chunk。

## Embedding 与 Chroma

- `POST /api/rag/documents/{document_id}/embeddings/rebuild`：按当前 Chunk 批量生成 Embedding 并写入 Chroma，需要 `document:embed`。
- `DELETE /api/rag/documents/{document_id}/embeddings`：删除该文档在 Chroma 中的向量并将 Chunk 状态重置为 `PENDING`，需要 `document:embed`。

重建响应包含 `batch_id`、模型名、文档版本对应的批次统计和 `embedded_count`。模型或 Chroma 失败时返回 `EMBEDDING_FAILED` 或 `CHROMA_WRITE_FAILED`，并通过 `retryable` 标记是否可以重试。

## RAG 检索

- `POST /api/rag/search`：执行向量与关键词混合检索，支持 `facility_type`、`region`、`version`、`as_of_date`、`top_k` 和 `rerank`。
- `POST /api/rag/search/debug`：返回同样的检索结果及召回数量、合并数量、模型和耗时等调试信息。

两个接口需要 `document:read` 权限；结果包含文档名、页码、Chunk ID、相似度、metadata 和原文片段。
