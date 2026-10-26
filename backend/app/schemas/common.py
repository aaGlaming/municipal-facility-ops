from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    code: str
    message: str
    trace_id: str
    retryable: bool


class StatusUpdateRequest(BaseModel):
    status: str
    idempotency_key: str = Field(min_length=1, max_length=128)


class HealthResponse(BaseModel):
    status: str
    trace_id: str
    checks: dict[str, Any] | None = None


class ReadinessResponse(HealthResponse):
    code: str | None = None
    message: str | None = None
    retryable: bool | None = None
