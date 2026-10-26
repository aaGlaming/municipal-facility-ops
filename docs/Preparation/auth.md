# 认证与权限接口

## 登录

`POST /api/auth/login`

```json
{"username":"dispatcher","password":"<configured password>"}
```

返回 `access_token`、`token_type` 和 `expires_in`。未配置 bootstrap 凭据时返回 `AUTH_NOT_CONFIGURED`。

## 当前用户

`GET /api/auth/me` 需要 Bearer Token，返回 subject、角色、权限、区域和可见菜单。

## 受保护接口

- `GET /api/facilities`：需要 `facility:read`，支持 `region` 查询参数。
- `POST /api/work-orders/{work_order_id}/status`：需要 `work_order:write`；关闭工单必须在请求体中传 `human_confirmation: true`。

统一错误响应包含 `code`、`message`、`trace_id` 和 `retryable`。常见代码包括 `AUTHENTICATION_REQUIRED`、`INVALID_TOKEN`、`PERMISSION_DENIED`、`REGION_SCOPE_DENIED` 和 `HUMAN_CONFIRMATION_REQUIRED`。
