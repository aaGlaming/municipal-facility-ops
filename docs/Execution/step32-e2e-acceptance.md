# Step 32：执行端到端业务验收

## 验收链路

新增 `backend/tests/test_e2e_acceptance.py`，在隔离 SQLite fixture 中串联验证：

1. 创建问题上报，检查来源标签、区域和幂等重复请求。
2. 执行分诊类别/优先级判断和 SLA 计划计算。
3. 推进问题状态 `NEW -> TRIAGED -> LINKED`。
4. 创建巡检任务，完成派工、开始和完成，并保留结果说明。
5. 创建工单，推进 `NEW -> TRIAGED -> ASSIGNED -> IN_PROGRESS -> WAITING_CONFIRMATION -> COMPLETED`。
6. 提交维修说明和证据 URI，执行验收并关闭工单。
7. 创建高风险 Agent 运行，验证人工确认后才进入 `SUCCEEDED`。
8. 读取审计流，确认报修创建、工单状态变更和验收事件可追溯。

## 边界验证

- 重复报修请求通过幂等键返回原记录，不重复创建。
- 区域用户访问 `DISTRICT-99` 被 `REGION_SCOPE_DENIED` 拒绝。
- 缺少 `audit:read` 的用户无法读取审计记录。
- 工单关闭必须携带人工确认和证据链；高风险 Agent 在确认前保持 `WAITING_CONFIRMATION`。
- 证据 URI、来源类型、区域、状态变更和审计事件均有可复核断言。

## 校验记录

- Step32 定向验收：2 passed。
- `pytest -q backend/tests`：86 passed。
- Ruff 检查和格式检查：通过。
- `git diff --check`：通过。

## 复现命令

```powershell
pytest -q backend/tests/test_e2e_acceptance.py
pytest -q backend/tests
```

该验收在本地测试客户端和固定 SQLite fixture 中重复执行，不依赖外部 MCP；Step33 再验证真实 MySQL、Chroma、模型和前端浏览器环境。
