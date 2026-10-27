# Step 19：实现 Agent 工具层

## 已实现能力

- 新增 `backend/app/tools/runner.py` 作为统一工具执行网关，所有 Agent 工具都先经过注册表白名单、Pydantic 参数校验、权限校验、人工确认和幂等检查。
- 接入设施查询、设施历史、RAG 检索、SLA 计算、人员/供应商容量、问题上报、巡检创建/派工/结果更新、工单创建/派工/状态更新/SLA 升级、安全清单、验收和审计工具。
- 只读工具返回受限字段和分页结果；写工具复用现有业务服务的区域、状态机、容量、人员/供应商和业务约束。
- 高风险派工、工单状态更新和验收在没有人工确认时返回 `PENDING_CONFIRMATION`，不会写入业务表。
- `tool_calls` 表记录工具请求、响应、风险、确认状态、幂等键和执行时间；相同 `agent_run_id + idempotency_key` 重复调用返回 `DUPLICATE` 和原调用结果。
- 失败结果统一包含错误码、消息、可重试标记和恢复信息；工具执行和权限/确认拒绝都写入安全审计事件。

## 工具入口

```python
from app.tools.runner import execute_tool

result = execute_tool(db, principal, request, tool_call_request, settings)
```

工具调用请求必须包含 `agent_name`、`agent_run_id`、`trace_id`、`tool_name`、参数和幂等键。工具名称和参数不能由模型绕过 `TOOL_CONTRACTS` 直接执行。

## 数据库迁移

- 全新数据库的 `infra/mysql/init/001_schema.sql` 已为 `tool_calls` 增加 `human_confirmation`。
- 已有 MySQL 实例执行 `infra/mysql/init/006_step19_tool_calls.sql`。

## 验证结果

- `pytest -q`：57 passed
- `python -m ruff check backend/app backend/tests`：通过
- `python -m ruff format --check backend/app backend/tests`：通过

Step20 将在此工具层之上实现 Supervisor、Agent 路由和循环预算控制。
