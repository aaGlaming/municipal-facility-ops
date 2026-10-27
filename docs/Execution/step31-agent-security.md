# Step 31：执行 Agent 评测与安全验证

## 评测与验证内容

- 新增 Agent 路由 Gold Set，覆盖分诊、设施、SLA、巡检、派工、安全、验收 7 类意图。
- 校验工具目录完整性、Agent 白名单、工具参数 schema、未知工具拒绝和无效参数拦截。
- 验证提示注入文本不会直接触发工具执行，恶意内容仍按普通问题描述处理。
- 验证未认证访问、缺少权限的 Agent/RAG 查询、区域越权和高风险工单状态变更的拒绝/确认边界。
- 验证 Token 等敏感值不会写入结构化日志和 JSONL 审计。
- 已将发现按严重级别、复现步骤、修复状态和回归测试写入 `evaluation/reports/step31-agent-security.json`。

## 基线结果

- Agent 路由准确率：`1.0`（7 条）。
- 工具未知名称与无效参数：均被网关拒绝，返回 `TOOL_NOT_FOUND` / `INVALID_ARGUMENT`。
- 提示注入边界：通过。
- 敏感日志/审计脱敏：通过。
- 工具契约目录完整性：通过。
- 当前报告中的 SEC-001 至 SEC-004 均为 `MITIGATED`，严重级别为 HIGH/CRITICAL，并关联回归测试。

## 执行命令

```powershell
$env:PYTHONPATH='backend'; python scripts/evaluate_agent_security.py
pytest -q backend/tests
```

## 校验记录

- Agent 安全评测脚本：通过。
- `pytest -q backend/tests`：84 passed。
- Ruff 检查与格式检查：通过。
- `git diff --check`：通过。

Step32/33 继续在真实依赖环境补充端到端、超时和服务不可用故障注入；外部 MCP 不参与指标计算。
