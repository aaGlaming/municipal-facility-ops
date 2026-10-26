# Step 9：实现数据库初始化与种子导入

依据：`D:\LEARN\AI\programs\AgentTask\Projects\municipal-facility-ops\docs\municipal-facility-ops.md`

## 状态

**完成**。本步骤未推进 Step 10。

## 交付物

- [seed_database.py](../../scripts/seed_database.py)：构建 seed plan、执行校验、事务批量导入和回滚。
- [test_seed_database.py](../../backend/tests/test_seed_database.py)：外键、状态、时间顺序和幂等键测试。
- [seed_imports.jsonl](../../data/manifests/seed_imports.jsonl)：每次导入批次、行数、状态、耗时和失败信息。
- `data/manifests/manifest.json` 已登记批次日志文件的行数、字节数和 SHA256。

## 导入批次

- 批次 ID：`step09-20261026`
- 数据库：本地 MySQL `municipal_ops`
- 导入结果：成功
- 重复执行：成功，行数保持不变
- 事务边界：每个批次单事务，异常自动 rollback 并写入失败日志。
- 批次日志保留一次故障回滚记录和两次成功记录，用于验证失败可定位、修复后可恢复。

| 表 | 导入行数 |
|---|---:|
| `roles` | 5 |
| `permissions` | 5 |
| `role_permissions` | 12 |
| `users` / `user_roles` | 100 / 100 |
| `locations` | 500 |
| `facilities` | 500 |
| `technicians` | 100 |
| `vendors` | 40 |
| `sla_rules` | 32 |
| `citizen_reports` | 63,200 |
| `inspection_tasks` | 1,600 |
| `work_orders` | 1,800 |
| `acceptance_records` | 900 |
| `agent_runs` | 1,200 |
| `tool_calls` | 0 |
| `audit_logs` | 1,800 |

公开清洗事件和合成报修均写入 `citizen_reports`，通过 `source_type`、`source_system` 和 `data_version` 区分来源。

## 验证结果

- dry-run 校验无错误。
- 工单、报修、巡检、验收和审计外键孤儿记录均为 0。
- 工单截止时间早于创建时间的记录为 0。
- 工单幂等键重复数为 0。
- 不合法来源标签记录为 0。
- 审计事件哈希为空记录为 0。
- 数据库当前没有执行 Step 10 应用初始化之外的操作；模型服务和 FastAPI 依赖未在本步骤改动。
