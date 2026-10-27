# Step20：Supervisor 与 Agent 循环控制

## 实现内容

- `backend/app/agents/supervisor.py` 提供 `Supervisor`、`SupervisorDecision`、`route_intent` 和 `build_supervisor`。
- Supervisor 根据意图路由到 `triage`、`facility`、`sla`、`inspection`、`dispatch`、`safety`、`acceptance` 七类 Agent。
- 模型输出必须符合结构化决策契约；工具调用统一进入 Step19 的 `execute_tool` 网关，模型不能绕过权限、参数、业务状态和幂等校验。
- 循环受模型调用数、工具调用数和时间预算限制；连续两次工具结果无变化时以 `NO_PROGRESS` 停止。
- 模型未配置时以 `EVIDENCE_INSUFFICIENT` 停止；工具返回高风险确认时进入 `WAITING_CONFIRMATION`。
- `agent_runs` ORM 模型和迁移记录运行状态、迭代数、输入/输出 token、Prompt 版本、停止原因和时间。

## 运行示例

```python
from app.agents.supervisor import Supervisor

response = Supervisor(model=model_adapter).run(
    db, principal, request, agent_request
)
```

`model_adapter` 接收当前 `AgentState`，返回 `SupervisorDecision` 或等价字典。生产环境应由模型适配层提供该函数，测试环境可注入确定性函数。

## 停止原因

`COMPLETED`、`EVIDENCE_INSUFFICIENT`、`HUMAN_CONFIRMATION_REQUIRED`、`MAX_MODEL_CALLS`、`MAX_TOOL_CALLS`、`NO_PROGRESS`、`TIMEOUT`、`FAILED` 等停止原因会写入响应和 `agent_runs`。

## 验证

- Step20 定向测试：4 passed
- 全量测试：61 passed
