from fastapi import APIRouter, Request

from app.schemas.common import HealthResponse


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    return HealthResponse(status="ok", trace_id=request.state.trace_id)


@router.get("/ready", response_model=HealthResponse)
def ready(request: Request) -> HealthResponse:
    return HealthResponse(
        status="ready",
        trace_id=request.state.trace_id,
        checks={"mysql": "deferred", "chroma": "deferred", "llm": "deferred"},
    )
