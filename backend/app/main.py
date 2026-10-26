import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import facilities, health, work_orders
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, request_log_fields

logger = logging.getLogger(__name__)


def _request_id(value: str | None) -> str:
    candidate = (value or "").strip()
    if (
        candidate
        and len(candidate) <= 128
        and all(character.isprintable() and character not in "\r\n" for character in candidate)
    ):
        return candidate
    return str(uuid4())


def _error_response(request: Request, status_code: int, code: str, message: str, retryable: bool) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "trace_id": getattr(request.state, "trace_id", ""),
            "retryable": retryable,
        },
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    runtime_settings = settings or get_settings()
    configure_logging(runtime_settings.log_level)
    application = FastAPI(
        title="Municipal Facility Operations API",
        version="0.1.0",
        description="市政设施巡检与维修平台基础 API",
        contact={"name": "Municipal Facility Operations"},
    )
    application.state.settings = runtime_settings
    application.add_middleware(
        CORSMiddleware,
        allow_origins=runtime_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-Id", "X-Trace-Id"],
        expose_headers=["X-Request-Id", "X-Trace-Id"],
    )

    @application.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        started_at = time.perf_counter()
        request.state.request_id = _request_id(request.headers.get("X-Request-Id"))
        request.state.trace_id = _request_id(request.headers.get("X-Trace-Id"))
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("unhandled request error", extra=dict(request_log_fields(request, 500, started_at)))
            raise
        response.headers["X-Request-Id"] = request.state.request_id
        response.headers["X-Trace-Id"] = request.state.trace_id
        logger.info("request completed", extra=dict(request_log_fields(request, response.status_code, started_at)))
        return response

    @application.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        detail: dict[str, object] = exc.detail if isinstance(exc.detail, dict) else {}
        return _error_response(
            request,
            exc.status_code,
            str(detail.get("code", "HTTP_ERROR")),
            str(detail.get("message", exc.detail)),
            bool(detail.get("retryable", exc.status_code >= 500)),
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.info(
            "request validation failed",
            extra={"trace_id": request.state.trace_id, "request_id": request.state.request_id},
        )
        return _error_response(request, 422, "VALIDATION_ERROR", "请求参数校验失败", False)

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(
            "unhandled application error",
            extra={"trace_id": request.state.trace_id, "request_id": request.state.request_id},
        )
        return _error_response(request, 500, "INTERNAL_ERROR", "服务内部错误", True)

    application.include_router(health.router)
    application.include_router(facilities.router)
    application.include_router(work_orders.router)
    return application


app = create_app()
