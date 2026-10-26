# FastAPI 基础 API

服务默认地址：`http://127.0.0.1:8000`

## 请求上下文

- 可选请求头：`X-Request-Id`、`X-Trace-Id`。
- 服务会在响应中回传这两个请求头。
- 未提供或超过 128 个字符的值会被替换为服务端生成的 UUID。

## 健康检查

### `GET /health`

进程存活检查，不访问 MySQL、Chroma 或模型服务。

```json
{
  "status": "ok",
  "trace_id": "..."
}
```

### `GET /ready`

检查 MySQL、Chroma 和 LLM。依赖不完整时返回 HTTP 503：

```json
{
  "status": "not_ready",
  "checks": {"mysql": "ok", "chroma": "ok", "llm": "not_configured"},
  "code": "DEPENDENCY_NOT_READY",
  "message": "一个或多个依赖服务不可用",
  "trace_id": "...",
  "retryable": true
}
```

## 统一错误

```json
{
  "code": "VALIDATION_ERROR",
  "message": "请求参数校验失败",
  "trace_id": "...",
  "retryable": false
}
```

完整 OpenAPI 描述由 FastAPI 在 `/openapi.json` 提供。
