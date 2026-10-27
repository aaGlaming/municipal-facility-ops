"""Stable request, state, observation and tool-call contracts for Agent runs."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

AgentName = Literal["supervisor", "triage", "facility", "sla", "inspection", "dispatch", "safety", "acceptance"]
RunStatus = Literal["PENDING", "RUNNING", "WAITING_CONFIRMATION", "SUCCEEDED", "FAILED", "CANCELLED"]
PlanStepStatus = Literal["PENDING", "RUNNING", "SUCCEEDED", "FAILED", "SKIPPED"]
ObservationSource = Literal["model", "tool", "system", "human"]
ConfirmationDecision = Literal["PENDING", "APPROVED", "REJECTED", "EXPIRED"]
ToolCallStatus = Literal["SUCCEEDED", "DUPLICATE", "FAILED", "PENDING_CONFIRMATION"]
StopReason = Literal[
    "COMPLETED",
    "EVIDENCE_INSUFFICIENT",
    "HUMAN_CONFIRMATION_REQUIRED",
    "MAX_MODEL_CALLS",
    "MAX_TOOL_CALLS",
    "NO_PROGRESS",
    "TIMEOUT",
    "RETRY_EXHAUSTED",
    "PERMISSION_DENIED",
    "VALIDATION_FAILED",
    "FAILED",
    "CANCELLED",
]


class AgentRequest(BaseModel):
    """Immutable input envelope passed to a LangGraph run."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1, max_length=128)
    trace_id: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)
    user_id: str = Field(min_length=1, max_length=128)
    agent_name: AgentName
    intent: str = Field(min_length=1, max_length=1000)
    input: dict[str, Any] = Field(default_factory=dict)
    region: str | None = Field(default=None, max_length=100)
    max_model_calls: int = Field(default=8, ge=1, le=8)
    max_tool_calls: int = Field(default=16, ge=1, le=16)
    timeout_seconds: int = Field(default=90, ge=1, le=900)


class AgentPlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(min_length=1, max_length=64)
    objective: str = Field(min_length=1, max_length=500)
    tool_name: str | None = Field(default=None, max_length=128)
    status: PlanStepStatus = "PENDING"
    requires_confirmation: bool = False
    depends_on: list[str] = Field(default_factory=list, max_length=16)


class AgentPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str = Field(min_length=1, max_length=64)
    objective: str = Field(min_length=1, max_length=1000)
    steps: list[AgentPlanStep] = Field(default_factory=list, max_length=32)
    created_at: datetime
    revision: int = Field(default=1, ge=1)


class AgentObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1, max_length=64)
    source: ObservationSource
    summary: str = Field(min_length=1, max_length=2000)
    data: dict[str, Any] = Field(default_factory=dict)
    tool_call_id: str | None = Field(default=None, max_length=64)
    created_at: datetime


class EvidenceCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    citation_id: str = Field(min_length=1, max_length=64)
    source_type: Literal["rag", "database", "user", "tool"]
    document_id: str | None = Field(default=None, max_length=64)
    chunk_id: str | None = Field(default=None, max_length=64)
    source_name: str | None = Field(default=None, max_length=255)
    page_number: int | None = Field(default=None, ge=1)
    snippet: str = Field(min_length=1, max_length=2000)
    similarity: float | None = Field(default=None, ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=1000)
    retryable: bool
    phase: Literal["planning", "model", "tool", "validation", "authorization", "persistence", "timeout"]
    tool_call_id: str | None = Field(default=None, max_length=64)
    recovery_hint: str | None = Field(default=None, max_length=500)
    details: dict[str, Any] = Field(default_factory=dict)


class HumanConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation_id: str = Field(min_length=1, max_length=64)
    action: str = Field(min_length=1, max_length=128)
    summary: str = Field(min_length=1, max_length=1000)
    risk_level: Literal["HIGH", "CRITICAL"]
    decision: ConfirmationDecision = "PENDING"
    requested_at: datetime
    expires_at: datetime | None = None
    decided_by: str | None = Field(default=None, max_length=128)
    decided_at: datetime | None = None
    reason: str | None = Field(default=None, max_length=1000)


class ToolCallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_call_id: str = Field(min_length=1, max_length=64)
    agent_run_id: str = Field(min_length=1, max_length=64)
    trace_id: str = Field(min_length=1, max_length=128)
    agent_name: AgentName
    tool_name: str = Field(pattern=r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$", max_length=128)
    arguments: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=16, max_length=255)
    human_confirmation: bool = False


class ToolFailure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=1000)
    retryable: bool
    recovery_hint: str | None = Field(default=None, max_length=500)
    details: dict[str, Any] = Field(default_factory=dict)


class ToolCallResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_call_id: str = Field(min_length=1, max_length=64)
    tool_name: str = Field(pattern=r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$", max_length=128)
    status: ToolCallStatus
    result: dict[str, Any] = Field(default_factory=dict)
    error: ToolFailure | None = None
    idempotency_key: str = Field(min_length=16, max_length=255)
    duplicate_of: str | None = Field(default=None, max_length=64)


class AgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_run_id: str = Field(min_length=1, max_length=64)
    trace_id: str = Field(min_length=1, max_length=128)
    status: RunStatus
    stop_reason: StopReason | None = None
    answer: str | None = None
    observations: list[AgentObservation] = Field(default_factory=list)
    evidence: list[EvidenceCitation] = Field(default_factory=list)
    pending_confirmation: HumanConfirmation | None = None
    errors: list[AgentError] = Field(default_factory=list)


def build_idempotency_key(trace_id: str, tool_name: str, business_id: str, arguments: dict[str, Any]) -> str:
    """Build a stable key without persisting raw tool arguments."""

    request_hash = hashlib.sha256(
        json.dumps(arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:32]
    return f"{trace_id}:{tool_name}:{business_id}:{request_hash}"
