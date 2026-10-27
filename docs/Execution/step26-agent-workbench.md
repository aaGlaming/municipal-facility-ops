# Step26：前端 Agent 与工单交互

## 实现内容

- 新增受控 Agent 运行 API：发起运行、读取运行和 trace、人工确认/拒绝、取消和重试。
- Agent 工作台支持报修文本、区域、意图和附件元数据输入。
- 运行卡片展示 `agent_run_id`、`trace_id`、运行阶段、观察、工具轨迹、最终建议和错误。
- 高风险请求进入 `WAITING_CONFIRMATION`，前端提供确认执行和拒绝操作；取消和重试也通过受控 API 完成。
- 工单中心接入 `/api/work-orders`，展示优先级、状态、SLA 截止时间、派工人员和状态推进操作；高风险状态推进弹出人工确认。
- 后端 Agent 运行入口按用户权限保护，并对运行记录做用户范围隔离；不通过外部 MCP 执行业务动作。

## 验证

- Agent API 定向测试：3 passed
- 全量后端测试：78 passed
- `npm run type-check`：通过
- `npm run build`：通过
- 构建产物未提交，`dist/` 保持忽略。
