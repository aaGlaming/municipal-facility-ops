from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

from app.api.routes import facilities, health, work_orders

app = FastAPI(title="Municipal Facility Operations", version="0.1.0")


@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    request.state.trace_id = request.headers.get("X-Trace-Id", str(uuid4()))
    response = await call_next(request)
    response.headers["X-Trace-Id"] = request.state.trace_id
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail: dict[str, object] = exc.detail if isinstance(exc.detail, dict) else {}
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": detail.get("code", "HTTP_ERROR"),
            "message": detail.get("message", str(exc.detail)),
            "trace_id": request.state.trace_id,
            "retryable": detail.get("retryable", exc.status_code >= 500),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_ERROR",
            "message": "服务内部错误",
            "trace_id": request.state.trace_id,
            "retryable": True,
        },
    )


app.include_router(health.router)
app.include_router(facilities.router)
app.include_router(work_orders.router)
