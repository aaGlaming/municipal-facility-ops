# Step 27：实现前端 RAG 管理与检索展示

## 完成内容

- 新增 `GET /api/rag/documents`，支持分页、状态、区域、设施类型和版本过滤，并沿用当前用户区域权限范围。
- 将 RAG 路由接入 `RagWorkbench`，提供文档管理、Chunk 预览、向量入库和检索调试四个入口。
- 文档管理支持文件上传、区域/设施类型/版本填写、解析状态、失败原因、文件大小和刷新列表。
- Chunk 预览支持选择文档并展示页码、标题、Token 数、原文片段和 Chunk ID。
- 向量入库支持按文档触发 Embedding 重建，并提示 Embedding 端点或 Chroma 不可用时的重试方向。
- 检索调试支持查询词、区域、设施类型、版本、Top-K 和 rerank；结果展示相似度、文档、页码、Chunk ID、文档 ID、来源版本、metadata 和原文片段。
- 页面统一处理无结果、服务错误、解析失败和权限不足等状态，操作按钮按权限禁用。

## 校验记录

- `npm run type-check`：通过。
- `npm run build`：通过；Vite 输出现有 bundle 体积提示，不影响构建结果。
- `python -m ruff check backend/app backend/tests`：通过。
- `python -m ruff format --check backend/app backend/tests`：通过。
- `pytest -q backend/tests`：78 passed。
- `git diff --check`：通过。

## 相关文件

- `backend/app/api/routes/rag.py`
- `backend/app/services/document_service.py`
- `backend/app/schemas/rag.py`
- `frontend/src/views/RagWorkbench.vue`
- `frontend/src/router/index.ts`
