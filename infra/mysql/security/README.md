# MySQL 权限边界

`001_app_role.sql.template` 是 DBA 执行模板，不包含可用密码。渲染前必须在受控环境中替换 `REPLACE_WITH_SECRET`，执行后应删除渲染文件。

应用角色只获得 `SELECT`、`INSERT`、`UPDATE`、`DELETE`。数据库建表、迁移、账号管理和授权操作使用单独的管理员身份，不进入应用连接串。

当前本地 `municipal` 账号由 Step 4 创建，尚未拥有 `CREATE USER` 或 `CREATE ROLE` 权限，因此本步骤只提交最小权限模板，不擅自修改该账号的管理员授权。后续配置真实应用账号时应由 DBA 执行模板并复核 `SHOW GRANTS`。
