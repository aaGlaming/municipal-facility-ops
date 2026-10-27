# Step 28：完善日志、审计和运行监控

## 完成内容

- 统一结构化日志字段：`request_id`、`trace_id`、`agent_run_id`、`tool_call_id`、`user_id`、状态码、耗时、输入/输出 token、成本、重试次数和错误码。
- 日志和安全审计统一做敏感字段脱敏，令牌、密码、API Key、Authorization 和 Cookie 不进入日志或审计详情。
- Agent Supervisor 修正 token 统计，记录运行耗时、token、成本和失败停止原因；运行记录仍保存到 `agent_runs`。
- 新增进程内请求指标：请求数、错误数、错误率、P50/P95 延迟和依赖健康状态。
- 新增 `/api/monitoring/overview`、`/api/monitoring/runs`、`/api/monitoring/audit` 和告警关闭接口，分别受 `agent:read`、`audit:read`、`audit:write` 权限保护。
- 监控页面替换运行/审计占位页，展示运行记录、依赖健康、错误率、延迟、token、停止原因、追加审计事件和可关闭告警。
- 当 5xx 错误率、P95 延迟或 MySQL/Chroma/模型依赖异常时生成可追踪告警；告警 ID、状态、打开/关闭时间和详情均返回前端。

## 校验记录

- `python -m ruff check backend/app backend/tests`：通过。
- `python -m ruff format --check backend/app backend/tests`：通过。
- `pytest -q backend/tests`：80 passed。
- `npm run type-check`：通过。
- `npm run build`：通过；Vite 仍提示现有 bundle 体积偏大，不影响构建。
- `git diff --check`：通过。

## 相关文件

- `backend/app/core/logging.py`
- `backend/app/core/monitoring.py`
- `backend/app/api/routes/monitoring.py`
- `backend/app/services/audit_service.py`
- `backend/app/agents/supervisor.py`
- `frontend/src/views/RecordsView.vue`
- `backend/tests/test_monitoring.py`
