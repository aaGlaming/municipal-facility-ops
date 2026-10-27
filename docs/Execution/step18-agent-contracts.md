# Step 18：Agent 状态与工具契约

## 状态契约

`backend/app/schemas/agent.py` 定义了 Agent 运行的统一数据结构：

- `AgentRequest`：`request_id`、`trace_id`、`session_id`、`user_id`、Agent 名称、意图、输入和运行预算。
- `AgentPlan`/`AgentPlanStep`：计划版本、步骤目标、依赖、工具名称和确认要求。
- `AgentObservation`：模型、工具、系统或人工产生的结构化观察。
- `EvidenceCitation`：RAG/数据库/工具证据的来源、文档、页码、Chunk、片段和相似度。
- `AgentError`：错误码、阶段、可重试标记、恢复提示和安全的附加信息。
- `HumanConfirmation`：高风险动作、风险等级、确认状态、确认人、时间和理由。
- `ToolCallRequest`/`ToolCallResult`：工具调用上下文、参数、幂等键、重复结果和失败语义。
- `AgentResponse`：最终状态、停止原因、回答、证据、观察、待确认动作和错误列表。

`backend/app/memory/state.py` 提供 LangGraph 使用的 `AgentState` TypedDict，固定保存当前节点、计划、观察、证据、工具结果、错误、确认、调用计数、无进展计数和时间边界；观察、证据、工具结果和错误字段使用 `operator.add` reducer 追加，避免并行节点覆盖彼此结果。`initial_agent_state` 会创建空集合和零计数，避免不同运行共享状态。

停止原因包括完成、证据不足、需要人工确认、模型/工具调用上限、连续无进展、超时、重试耗尽、权限拒绝、校验失败和取消。

## 工具契约

`backend/app/tools/contracts.py` 为 13 个工具登记输入 schema、输出 schema、允许的 Agent、权限、风险等级、人工确认策略、错误码、可重试错误、幂等要求和审计动作。工具采用 `domain.verb` 命名并由 `AGENT_TOOL_WHITELIST` 生成每个 Agent 的白名单。

| 工具 | 风险 | 确认 | 幂等 | 允许的主要 Agent |
| --- | --- | --- | --- | --- |
| `facility.search` / `facility.history` | READ_ONLY | NEVER | 否 | triage、facility、inspection |
| `rag.search` | READ_ONLY | NEVER | 否 | supervisor、triage、facility、sla、safety、acceptance |
| `sla.calculate` / `staff.capacity` | READ_ONLY | NEVER | 否 | sla、inspection、dispatch |
| `report.create` / `inspection.create` / `work_order.create` | WRITE | OPTIONAL | 是 | triage、inspection、sla、dispatch |
| `work_order.assign` / `work_order.update_status` | HIGH | REQUIRED | 是 | dispatch、triage、acceptance |
| `safety.checklist` | READ_ONLY | NEVER | 否 | safety、dispatch、acceptance |
| `acceptance.submit` | HIGH | REQUIRED | 是 | acceptance |
| `audit.record` | WRITE | NEVER | 是 | 所有 Agent |

所有写工具的幂等键由 `build_idempotency_key(trace_id, tool_name, business_id, arguments)` 生成。原始参数只参与 SHA256，不写入幂等键；重复调用的返回状态为 `DUPLICATE` 并携带原调用标识。

工具错误必须包含错误码、可重试标记和恢复提示。数据库/外部服务不可用属于可重试错误；参数、权限、状态机、区域和人工确认失败属于不可重试或需要人工处理的错误。

## 验证结果

- `pytest -q`：52 passed
- `python -m ruff check backend/app backend/tests`：通过
- `python -m ruff format --check backend/app backend/tests`：通过

Step18 只定义契约和白名单；具体工具执行逻辑由 Step19 实现，Supervisor 循环控制由 Step20 实现。
