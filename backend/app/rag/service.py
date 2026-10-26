# 文件职责：RAG 摄取和查询服务门面。
# 后续串联 load -> clean -> split -> embed -> Chroma upsert 和 query rewrite -> recall -> dedupe -> rerank -> Top-K。
# 每个阶段都要有运行 ID、状态、失败原因和可重试标记。
