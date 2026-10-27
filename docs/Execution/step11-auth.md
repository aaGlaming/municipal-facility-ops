# Step 11：认证与权限控制记录

## 实现内容

- `backend/app/core/auth.py` 提供 HS256 Bearer Token 签发、签名校验、过期校验、角色、权限和区域范围解析。
- `backend/app/api/routes/auth.py` 提供 `POST /api/auth/login` 和 `GET /api/auth/me`。
- `facility:read` 保护设施列表；`work_order:write` 保护工单状态更新。
- 区域范围在路由层、`work_order_service` 服务层和 `work_order_tools` 工具层重复执行，防止绕过入口调用。
- 关闭工单属于高风险动作，必须携带 `human_confirmation=true`；缺少确认时返回 `HUMAN_CONFIRMATION_REQUIRED`。
- 登录成功、登录失败、无效令牌、权限拒绝、区域范围拒绝和人工确认要求写入 `logs/security/security_events.jsonl`，该运行时日志已加入 Git 忽略。

## 权限和菜单映射

| 菜单 | 权限 |
| --- | --- |
| facilities | `facility:read` |
| work_orders | `work_order:read` |
| work_order_updates | `work_order:write` |
| audit | `audit:read` |
| agents | `agent:run` |
| users | `user:manage` |

管理员可通过 `*` 或 `admin:*` 权限访问所有接口；区域为 `*` 表示全域，其他用户只能访问令牌中的区域。

## 配置

复制 `backend/.env.example` 为本地 `backend/.env` 后设置 `AUTH_SECRET`、`AUTH_BOOTSTRAP_USERNAME` 和 `AUTH_BOOTSTRAP_PASSWORD`。示例文件不包含真实凭据。登录成功后使用 `Authorization: Bearer <access_token>` 调用受保护接口。

## 验证

执行结果：

- `python -m pytest -q`：23 passed
- `python -m ruff check backend scripts`：通过
- `python -m ruff format --check backend scripts`：通过

测试覆盖令牌往返和过期、未认证请求、权限不足、区域隔离、高风险人工确认和登录签发。Step 12 未执行。
