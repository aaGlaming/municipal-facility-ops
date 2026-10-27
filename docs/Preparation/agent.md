# Agent 与工具契约

Step18 的机器可读契约位于：

- `backend/app/schemas/agent.py`：运行请求、状态组成、证据、错误、人工确认和工具调用结果。
- `backend/app/memory/state.py`：LangGraph `AgentState` 和初始状态工厂。
- `backend/app/tools/contracts.py`：工具注册表、输入/输出 Pydantic schema、Agent 白名单和风险策略。
- `backend/app/tools/runner.py`：统一执行入口，负责 schema、权限、区域、状态、确认、幂等和审计。

调用方应先通过 `get_tool_contract(tool_name)` 获取契约，再执行参数校验、权限校验、区域校验、业务状态校验和人工确认校验。Step19 的工具实现不得绕过契约注册表直接接受模型生成的任意参数。

工具名统一使用 `domain.verb`，例如 `facility.search`、`rag.search`、`work_order.assign`。高风险工具必须返回 `PENDING_CONFIRMATION` 或 `HUMAN_CONFIRMATION_REQUIRED`，写工具必须使用稳定幂等键并记录审计动作。
