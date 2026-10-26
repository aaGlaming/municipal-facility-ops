# Step 8：设计 MySQL 数据模型

依据：`D:\LEARN\AI\programs\AgentTask\Projects\municipal-facility-ops\docs\municipal-facility-ops.md`

## 状态

**完成**。本步骤只创建和验证数据库结构，未执行 Step 9 的种子导入。

## 结构交付物

- [001_schema.sql](../../infra/mysql/init/001_schema.sql)：canonical MySQL 8.4 结构。
- [001_app_role.sql.template](../../infra/mysql/security/001_app_role.sql.template)：DBA 执行的最小权限应用角色模板。
- [verify_schema.py](../../scripts/verify_schema.py)：表、字段、索引、外键和审计触发器验证脚本。

已完成的核心表：

`users`、`roles`、`permissions`、`role_permissions`、`user_roles`、`locations`、`facilities`、`citizen_reports`、`inspection_tasks`、`work_orders`、`vendors`、`technicians`、`sla_rules`、`acceptance_records`、`agent_runs`、`tool_calls`、`audit_logs`。

## 设计约束

- 业务表统一保留 `source_type`、`source_system`、`data_version`、`version` 和 `is_deleted`。
- 工单、报修和工具调用保留幂等键；工单、设施、区域、状态、截止时间和 Agent trace 建立组合索引。
- 业务父记录采用 `ON DELETE RESTRICT`；用户、人员和供应商引用在账号/资源清理时使用 `ON DELETE SET NULL`；角色权限和用户角色使用 `ON DELETE CASCADE`。
- `audit_logs` 设计为追加写入，canonical schema 包含阻止 UPDATE/DELETE 的触发器；应用角色只允许对审计表 SELECT/INSERT。
- 高风险动作通过 `tool_calls.risk_level`、`human_confirmation` 和审计字段留痕，数据库不接受外部 MCP 直接写入。

## 验证结果

- 本地 `municipal_ops` 原有表在复核时均为 0 行，随后按 canonical schema 重建结构；Step 9 导入前已完成结构校验。
- `scripts/verify_schema.py --allow-missing-audit-triggers`：17 张表、关键字段、索引和外键通过。
- 本地 MySQL 开启 binary logging，而 Step 4 创建的 `municipal` 账号没有 SUPER/`log_bin_trust_function_creators` 权限，因此触发器创建被 MySQL 拒绝；canonical SQL 和 DBA 权限模板均已保留，需由 DBA 执行后再移除 `--allow-missing-audit-triggers`。
- 当前本地 `municipal` 账号仍是 Step 4 创建的开发账号，未擅自修改其授权；最小权限模板没有真实密码，避免把凭据写入仓库。
