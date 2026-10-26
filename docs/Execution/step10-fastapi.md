# Step 10：搭建 FastAPI 应用基础层

依据：`D:\LEARN\AI\programs\AgentTask\Projects\municipal-facility-ops\docs\municipal-facility-ops.md`

## 状态

**完成**。本步骤未推进 Step 11。

## 实现内容

- `backend/app/main.py`：`create_app` 应用工厂、CORS、请求上下文、统一异常处理和 OpenAPI 元数据。
- `backend/app/core/config.py`：环境变量加载、MySQL URL 校验、CORS 来源和运行参数。
- `backend/app/core/logging.py`：JSON 结构化日志，记录 request ID、trace ID、状态码和耗时，不记录请求正文或密钥。
- `backend/app/db/base.py`：SQLAlchemy `DeclarativeBase`。
- `backend/app/db/session.py`：连接池、预 ping、超时、回收和请求级 session 生命周期。
- `backend/app/core/dependencies.py`：配置和数据库 session 依赖注入入口。
- `backend/app/api/routes/health.py`：MySQL、Chroma 和 LLM 依赖检查。

## API 行为

- `GET /health` 只反映进程存活，始终不主动连接外部依赖。
- `GET /ready` 检查 MySQL、Chroma 和 LLM；全部正常返回 200，否则返回 503。
- 每个响应包含 `X-Request-Id` 和 `X-Trace-Id`；客户端提供的值会被限制长度并回传。
- HTTP 异常、请求校验错误和未处理异常统一返回 `code`、`message`、`trace_id`、`retryable`。
- 当前本地 `/ready` 结果为 MySQL `ok`、Chroma `ok`、LLM `not_configured`，因此返回 `503 DEPENDENCY_NOT_READY`。

## 验证

- API 测试：8 passed。
- 项目全量测试：18 passed。
- Ruff、格式检查、mypy 通过。
- OpenAPI 文档可从 `/openapi.json` 获取，接口说明见 `docs/Preparation/api.md`。
