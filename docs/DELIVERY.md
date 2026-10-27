# 项目交付总览

## 交付范围

本仓库交付市政设施巡检与维修平台的可验证工程实现：数据来源登记与清洗、MySQL 业务模型与种子、FastAPI API、认证权限、Agent 工具和循环、RAG 文档处理与检索、Vue 工作台、监控审计、评测和备份恢复。

## 当前状态

| 区域 | 状态 | 证据 |
|---|---|---|
| Step 1～7 数据与范围 | 完成 | `docs/Execution/step01-07-review.md` |
| Step 8～28 业务、Agent、RAG、前端 | 完成 | `docs/Execution/step-status.md` |
| Step 29～32 评测与离线验收 | 完成 | `evaluation/reports/` 与对应 Step 文档 |
| Step 33 本地最终验收 | 部分完成 | 本机缺少运行中的 MySQL、Chroma 和模型 |
| Step 34 备份恢复 | 部分完成 | 文件恢复通过；MySQL dump 待 Step36 |
| Step 35 文档整理 | 完成 | 本文档和 README |

## 新成员操作路径

1. 阅读 `docs/Preparation/architecture.md`、`requirements.md` 和 `data-dictionary.md`。
2. 复制 `.env.example` 并配置本地认证凭据；不要提交 `.env`。
3. 按 README 启动 FastAPI 和前端，访问 `/docs`、`/health`、`/ready`。
4. 运行 pytest、Ruff、前端 type-check/build。
5. 需要数据时先执行 `scripts/seed_database.py --dry-run`，再在已授权数据库执行正式导入。
6. 需要评测时运行 `evaluation/` 中的脚本并检查报告阈值和失败归因。
7. 需要交付备份时运行 `scripts/backup_restore.py`，核对 `manifest.json`、`restore-check` 和 `secrets_excluded`。

## API 与功能边界

API 路由按领域分为 auth、facilities、reports、inspections、work-orders、agents、rag 和 monitoring；完整参数、权限和错误格式见 `docs/Preparation/api.md`，机器可读契约由 `/openapi.json` 提供。高风险写操作经过工具网关、权限、状态机、幂等和人工确认，并写审计记录。

## 配置基线

配置模板位于 `backend/.env.example` 和 `frontend/.env.example`。核心变量包括 `MYSQL_URL`、`CHROMA_HOST/CHROMA_PORT`、`LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`、`EMBEDDING_MODEL`、`AUTH_SECRET`、`AUTH_BOOTSTRAP_*`、`RAG_*` 和 `AGENT_*`。开发示例值不能用于生产；凭据不得写入 Git、日志、评测数据或备份。

## 失败归因与已知限制

- `/ready` 返回 503：查看 `response.checks`，分别处理 MySQL、Chroma 或 LLM。
- RAG 失败：区分解析失败、无可用 Chunk、Embedding 超时、Chroma 写入失败和过滤后无召回；保留 document/chunk/batch ID 以便重试。
- Agent 停止：查看 `agent_runs` 的 `stop_reason`、`tool_calls` 和 `trace_id`；高风险或证据不足时人工确认是预期结果。
- Step33 和 Step34 的依赖阻断不是离线测试失败；待 Step36 Compose 启动真实依赖后补做 `/ready`、`mysqldump`、恢复查询和重启持久化验收。
