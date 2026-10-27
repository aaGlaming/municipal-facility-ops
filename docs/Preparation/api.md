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

## 设施

- `GET /api/facilities`：分页、类型、状态、区域、来源和关键词筛选。
- `GET /api/facilities/{facility_id}`：设施详情和位置。
- `GET /api/facilities/{facility_id}/events`：设施关联问题历史。
- `GET /api/facilities/nearby`：按 WGS84 坐标、半径和类型查询附近设施。

## 问题上报

- `POST /api/reports`：创建内部问题，支持 `idempotency_key` 和 `external_id`。
- `GET /api/reports`、`GET /api/reports/{report_id}`：按区域、状态、分类和来源查询。
- `PATCH /api/reports/{report_id}/status`：执行受控状态变更。
- `POST /api/reports/import/public`：导入公开事件，记录为 `source_type=public`。

## 巡检和工单

- `POST/GET /api/inspections`：创建和查询巡检任务。
- `PATCH /api/inspections/{task_id}/assign`：分配巡检人员。
- `PATCH /api/inspections/{task_id}/status`：开始、延期、恢复或完成巡检。
- `POST/GET /api/work-orders`：创建和查询工单。
- `POST /api/work-orders/{work_order_id}/status`：执行状态机流转。
- `POST /api/work-orders/{work_order_id}/acceptance`：提交验收结果和证据。
- `POST /api/work-orders/escalate-overdue`：将超 SLA 未终态工单升级。
