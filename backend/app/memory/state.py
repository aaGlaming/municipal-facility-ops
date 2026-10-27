"""Typed LangGraph state shared by the Supervisor and specialist nodes."""

from __future__ import annotations

from datetime import datetime
from operator import add
from typing import Annotated, TypedDict

from app.schemas.agent import (
    AgentError,
    AgentObservation,
    AgentPlan,
    AgentRequest,
    EvidenceCitation,
    HumanConfirmation,
    RunStatus,
    StopReason,
    ToolCallResult,
)


class AgentState(TypedDict, total=False):
    request: AgentRequest
    run_id: str
    status: RunStatus
    current_node: str | None
    plan: AgentPlan | None
    observations: Annotated[list[AgentObservation], add]
    evidence: Annotated[list[EvidenceCitation], add]
    tool_results: Annotated[list[ToolCallResult], add]
    errors: Annotated[list[AgentError], add]
    pending_confirmation: HumanConfirmation | None
    stop_reason: StopReason | None
    model_calls: int
    model_input_tokens: int
    model_output_tokens: int
    tool_calls: int
    no_progress_count: int
    progress_fingerprint: str | None
    started_at: datetime
    finished_at: datetime | None


def initial_agent_state(request: AgentRequest, run_id: str, started_at: datetime) -> AgentState:
    """Create a bounded, serializable state for a new graph execution."""

    return {
        "request": request,
        "run_id": run_id,
        "status": "PENDING",
        "current_node": None,
        "plan": None,
        "observations": [],
        "evidence": [],
        "tool_results": [],
        "errors": [],
        "pending_confirmation": None,
        "stop_reason": None,
        "model_calls": 0,
        "model_input_tokens": 0,
        "model_output_tokens": 0,
        "tool_calls": 0,
        "no_progress_count": 0,
        "progress_fingerprint": None,
        "started_at": started_at,
        "finished_at": None,
    }
