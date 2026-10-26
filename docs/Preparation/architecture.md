# 数据与系统边界

```text
公开数据/API ──> raw/public ──> prepare_data.py ──> processed ──> MySQL
维修规范文档 ──> raw/docs ──> 文档解析/切块/Embedding ──> Chroma
合成业务数据 ──> synthetic ──> MySQL seed

Vue ──> FastAPI Router ──> LangGraph Supervisor
                         ├─> 分诊/设施/巡检/调度/维修/验收 Agent
                         ├─> MySQL 业务工具
                         └─> Chroma RAG 检索
```

Agent 的建议和工具调用必须保留 `agent_run_id`，高风险的派工、状态关闭和验收动作需要权限校验、幂等键和审计记录。
