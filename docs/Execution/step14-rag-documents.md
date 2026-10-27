# Step 14：RAG 文档上传与解析

## 已实现能力

- `POST /api/rag/documents` 支持 PDF、DOCX、Markdown、TXT 和 HTML 上传。
- 校验文件名、扩展名、媒体类型、大小、NUL 字符、危险 HTML 标签、DOCX 压缩包路径和解压大小。
- 文件使用随机文档 ID 和安全相对路径保存到 `RAG_STORAGE_DIRECTORY`，不使用用户文件名作为目录路径。
- 按 SHA256 去重；相同文件重复上传返回 `DUPLICATE_DOCUMENT`。
- 保存上传人、设施类型、区域、生效日期、失效日期、版本、来源系统和来源类型。
- 解析结果保存为 `document_parts`，包括 part index、页码、标题、段落/表格文本和来源位置。
- PDF 按页解析，DOCX 解析段落与表格，Markdown 按标题/段落解析，HTML 提取标题、段落、列表和表格行。
- 解析失败仍保存原始文档，并将文档标记为 `FAILED`、写入失败原因和安全事件；接口返回 `DOCUMENT_PARSE_FAILED` 与文档 ID。
- 上传和查看分别受 `document:upload`、`document:read` 权限及区域范围控制。

## 数据库迁移

新增 `documents`、`document_parts` 表，已有 MySQL 实例使用 `infra/mysql/init/003_step14_documents.sql` 增量迁移。上传文件不进入 Git，`uploads/*` 已被忽略。

## 配置

- `RAG_STORAGE_DIRECTORY`：原始文件存储目录，默认 `uploads/documents`。
- `RAG_MAX_UPLOAD_BYTES`：单文件大小上限，默认 10 MiB。

## 验证结果

- `python -m pytest -q`：39 passed
- `python -m ruff check backend scripts`：通过
- `python -m ruff format --check backend scripts`：通过

Step 15 尚未开始。
