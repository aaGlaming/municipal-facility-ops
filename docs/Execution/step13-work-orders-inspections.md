# Step 13：工单与巡检业务模块

## 已实现能力

- 工单创建、详情、分页查询和区域筛选，创建时根据优先级计算 SLA 截止时间。
- 工单幂等键持久化，重复创建和重复状态请求返回相同业务结果。
- 工单状态机覆盖新建、分诊、派工、进行中、待确认、完成、验收、关闭、拒绝、阻塞、升级和取消；非法跳转返回结构化 409。
- 工单支持维修人员/供应商派工、处理说明和证据 URI；完成后可提交验收，拒绝后支持返工回到进行中。
- 超过 SLA 截止时间的未终态工单可批量升级为 `ESCALATED`，并保留区域权限边界。
- 巡检任务支持创建、分页查询、派工、开始、延期、恢复和完成，保存延期原因、完成说明和完成时间。
- 工单验收材料存入 `acceptance_records`，状态幂等事件存入 `work_order_status_events`；巡检结果说明和延期原因存入巡检任务记录。
- 已提供 `infra/mysql/init/002_step13_work_order_inspection.sql`，用于已有 MySQL 实例的增量迁移。

## 状态边界

工单状态只能沿预定义状态机流转。高风险关闭继续使用 Step11 的人工确认校验。巡检任务延期后必须先恢复到进行中才能完成，防止跳过执行过程。

## 验证结果

- `python -m pytest -q`：34 passed
- `python -m ruff check backend scripts`：通过
- `python -m ruff format --check backend scripts`：通过

Step 14 尚未开始。
