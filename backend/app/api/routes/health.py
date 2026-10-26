import logging
import urllib.error
import urllib.request

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.db.session import get_engine
from app.schemas.common import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


def check_mysql() -> str:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        logger.exception("mysql readiness check failed")
        return "unavailable"


def check_chroma(settings: Settings) -> str:
    url = f"http://{settings.chroma_host}:{settings.chroma_port}/api/v1/heartbeat"
    try:
        with urllib.request.urlopen(url, timeout=settings.db_connect_timeout_seconds) as response:
            return "ok" if 200 <= response.status < 300 else "unavailable"
    except (OSError, urllib.error.URLError):
        return "unavailable"


def check_llm(settings: Settings) -> str:
    if not settings.llm_configured:
        return "not_configured"
    url = f"{settings.llm_base_url.rstrip('/')}/models"
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {settings.llm_api_key}"})
    try:
        with urllib.request.urlopen(request, timeout=settings.db_connect_timeout_seconds) as response:
            return "ok" if 200 <= response.status < 300 else "unavailable"
    except (OSError, urllib.error.URLError):
        return "unavailable"


def check_dependencies(settings: Settings) -> dict[str, str]:
    return {"mysql": check_mysql(), "chroma": check_chroma(settings), "llm": check_llm(settings)}


@router.get("/health", response_model=HealthResponse, summary="进程存活检查")
def health(request: Request) -> HealthResponse:
    return HealthResponse(status="ok", trace_id=request.state.trace_id)


@router.get("/ready", response_model=ReadinessResponse, summary="依赖服务就绪检查")
def ready(request: Request) -> ReadinessResponse | JSONResponse:
    settings = getattr(request.app.state, "settings", None) or get_settings()
    checks = check_dependencies(settings)
    if not all(value == "ok" for value in checks.values()):
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "trace_id": request.state.trace_id,
                "checks": checks,
                "code": "DEPENDENCY_NOT_READY",
                "message": "一个或多个依赖服务不可用",
                "retryable": True,
            },
        )
    return ReadinessResponse(status="ready", trace_id=request.state.trace_id, checks=checks)
