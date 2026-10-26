# 文件职责：LangGraph Supervisor 和 Agent 路由图。
# 后续定义统一状态、节点、边、停止条件和错误分支。
# 根据用户意图选择 triage、facility、sla、inspection、dispatch、safety 或 acceptance Agent。
# 需要限制最大迭代次数、token 预算、超时，并把每次模型输出和工具调用写入 agent_runs。
