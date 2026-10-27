"""Bounded Supervisor loop for routing specialist Agents and executing tools."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from fastapi import Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.auth import AuthPrincipal
from app.core.config import Settings, get_settings
from app.memory.state import AgentState, initial_agent_state
from app.models.agent_run import AgentRun
from app.schemas.agent import (
    AgentError,
    AgentObservation,
    AgentRequest,
    AgentResponse,
    HumanConfirmation,
    ToolCallRequest,
    ToolCallResult,
    build_idempotency_key,
)
from app.tools.contracts import TOOL_CONTRACTS
from app.tools.runner import execute_tool

PROMPT_VERSION = "supervisor-v1"
SPECIALIST_AGENTS = ("triage", "facility", "sla", "inspection", "dispatch", "safety", "acceptance")


class SupervisorDecision(BaseModel):
    """Strict model output accepted by the Supervisor."""

    model_config = ConfigDict(extra="forbid")

    action: str = Field(pattern="^(tool|answer|wait_confirmation|stop)$")
    agent_name: str | None = None
    tool_name: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    answer: str | None = None
    summary: str | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    human_confirmation: bool = False


class SupervisorModel(Protocol):
    def __call__(self, state: AgentState) -> SupervisorDecision | dict[str, Any]: ...


def route_intent(intent: str) -> str:
    """Route an intent to one of the seven specialist Agents."""

    text = intent.lower()
    routes = (
        (("安全", "safety", "风险", "防护"), "safety"),
        (("验收", "acceptance", "通过", "拒收"), "acceptance"),
        (("巡检", "inspection", "检查"), "inspection"),
        (("派工", "调度", "dispatch", "维修人员", "vendor"), "dispatch"),
        (("sla", "时限", "超期", "优先级"), "sla"),
        (("设施", "facility", "位置", "台账", "历史"), "facility"),
    )
    for keywords, agent in routes:
        if any(keyword in text for keyword in keywords):
            return agent
    return "triage"


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _observation(
    source: str, summary: str, data: dict[str, Any] | None = None, tool_call_id: str | None = None
) -> AgentObservation:
    return AgentObservation(
        observation_id=f"OBS-{uuid4().hex[:16].upper()}",
        source=source,  # type: ignore[arg-type]
        summary=summary[:2000],
        data=data or {},
        tool_call_id=tool_call_id,
        created_at=_now(),
    )


class Supervisor:
    """Run a model-directed, bounded Supervisor loop.

    The model is injected so production can use an LLM while tests can use a
    deterministic decision function. Model output never executes directly:
    every tool call is validated by the Step19 execution gateway.
    """

    def __init__(self, model: SupervisorModel | None = None, settings: Settings | None = None) -> None:
        self.model = model
        self.settings = settings or get_settings()

    def run(
        self,
        db: Session,
        principal: AuthPrincipal,
        request: Request,
        agent_request: AgentRequest,
        *,
        run_id: str | None = None,
    ) -> AgentResponse:
        started = _now()
        run_id = run_id or f"RUN-{uuid4().hex[:16].upper()}"
        specialist = (
            agent_request.agent_name
            if agent_request.agent_name in SPECIALIST_AGENTS
            else route_intent(agent_request.intent)
        )
        state = initial_agent_state(agent_request.model_copy(update={"agent_name": specialist}), run_id, started)
        state["status"] = "RUNNING"
        self._save_run(db, state, specialist, status="RUNNING")
        deadline = time.monotonic() + agent_request.timeout_seconds
        final_answer: str | None = None

        if self.model is None or not self.settings.llm_configured:
            self._stop(state, "EVIDENCE_INSUFFICIENT", "未配置可用模型，无法生成可审计的 Agent 决策")
        else:
            while state["status"] == "RUNNING":
                if time.monotonic() >= deadline:
                    self._stop(state, "TIMEOUT", "Agent 执行超过时间预算")
                    break
                if state["model_calls"] >= agent_request.max_model_calls:
                    self._stop(state, "MAX_MODEL_CALLS", "达到模型调用预算")
                    break
                if state["tool_calls"] >= agent_request.max_tool_calls:
                    self._stop(state, "MAX_TOOL_CALLS", "达到工具调用预算")
                    break
                state["current_node"] = specialist
                try:
                    decision = self.model(state)
                    decision = (
                        decision
                        if isinstance(decision, SupervisorDecision)
                        else SupervisorDecision.model_validate(decision)
                    )
                except Exception as exc:
                    state["errors"].append(
                        AgentError(
                            code="MODEL_FAILED",
                            message="模型决策失败",
                            retryable=True,
                            phase="model",
                            details={"type": type(exc).__name__},
                        )
                    )
                    self._stop(state, "FAILED", "模型决策失败")
                    break
                state["model_calls"] += 1
                state["observations"].append(
                    _observation("model", decision.summary or decision.action, decision.model_dump(exclude_none=True))
                )
                state["model_input_tokens"] += decision.input_tokens
                state["model_output_tokens"] += decision.output_tokens

                if decision.action in {"answer", "stop"}:
                    final_answer = decision.answer or decision.summary
                    self._stop(
                        state, "COMPLETED" if decision.action == "answer" else "FAILED", final_answer or "模型停止执行"
                    )
                    break
                if decision.action == "wait_confirmation":
                    state["pending_confirmation"] = self._confirmation(decision, specialist)
                    state["status"] = "WAITING_CONFIRMATION"
                    state["stop_reason"] = "HUMAN_CONFIRMATION_REQUIRED"
                    break
                if decision.action != "tool" or not decision.tool_name:
                    self._stop(state, "VALIDATION_FAILED", "模型未提供合法工具调用")
                    break
                if decision.tool_name not in TOOL_CONTRACTS:
                    state["errors"].append(
                        AgentError(
                            code="TOOL_NOT_FOUND", message="模型选择了未注册工具", retryable=False, phase="validation"
                        )
                    )
                    self._stop(state, "VALIDATION_FAILED", "模型选择了未注册工具")
                    break
                call = ToolCallRequest(
                    tool_call_id=f"CALL-{uuid4().hex[:16].upper()}",
                    agent_run_id=run_id,
                    trace_id=agent_request.trace_id,
                    agent_name=decision.agent_name or specialist,  # type: ignore[arg-type]
                    tool_name=decision.tool_name,
                    arguments=decision.arguments,
                    idempotency_key=build_idempotency_key(
                        agent_request.trace_id, decision.tool_name, agent_request.request_id, decision.arguments
                    ),
                    human_confirmation=decision.human_confirmation,
                )
                result = execute_tool(db, principal, request, call, self.settings)
                state["tool_calls"] += 1
                state["tool_results"].append(result)
                state["observations"].append(
                    _observation(
                        "tool",
                        f"{result.tool_name}: {result.status}",
                        result.model_dump(mode="json"),
                        result.tool_call_id,
                    )
                )
                if result.status == "PENDING_CONFIRMATION":
                    state["pending_confirmation"] = self._confirmation_from_tool(result, specialist)
                    state["status"] = "WAITING_CONFIRMATION"
                    state["stop_reason"] = "HUMAN_CONFIRMATION_REQUIRED"
                    break
                if result.status == "FAILED" and result.error and not result.error.retryable:
                    state["errors"].append(
                        AgentError(
                            code=result.error.code,
                            message=result.error.message,
                            retryable=False,
                            phase="tool",
                            tool_call_id=result.tool_call_id,
                        )
                    )
                    self._stop(state, "FAILED", result.error.message)
                    break
                fingerprint = hashlib.sha256(
                    json.dumps(result.model_dump(mode="json"), sort_keys=True, default=str).encode()
                ).hexdigest()
                if fingerprint == state.get("progress_fingerprint"):
                    state["no_progress_count"] += 1
                else:
                    state["no_progress_count"] = 0
                    state["progress_fingerprint"] = fingerprint
                if state["no_progress_count"] >= 2:
                    self._stop(state, "NO_PROGRESS", "连续迭代未产生新结果")
                    break

        if state["status"] == "RUNNING":
            self._stop(state, "FAILED", "Agent 未完成")
        finished = _now()
        state["finished_at"] = finished
        self._save_run(db, state, specialist, status=state["status"], finished_at=finished)
        return AgentResponse(
            agent_run_id=run_id,
            trace_id=agent_request.trace_id,
            status=state["status"],
            stop_reason=state.get("stop_reason"),
            answer=final_answer,
            observations=state.get("observations", []),
            evidence=state.get("evidence", []),
            pending_confirmation=state.get("pending_confirmation"),
            errors=state.get("errors", []),
        )

    @staticmethod
    def _confirmation(decision: SupervisorDecision, agent_name: str) -> HumanConfirmation:
        return HumanConfirmation(
            confirmation_id=f"CONF-{uuid4().hex[:16].upper()}",
            action=decision.tool_name or "agent_action",
            summary=decision.summary or decision.answer or "需要人工确认的操作",
            risk_level="HIGH",
            requested_at=_now(),
        )

    @staticmethod
    def _confirmation_from_tool(result: ToolCallResult, agent_name: str) -> HumanConfirmation:
        return HumanConfirmation(
            confirmation_id=f"CONF-{uuid4().hex[:16].upper()}",
            action=result.tool_name,
            summary=result.error.message if result.error else "需要人工确认的操作",
            risk_level="HIGH",
            requested_at=_now(),
        )

    @staticmethod
    def _stop(state: AgentState, reason: str, summary: str) -> None:
        state["stop_reason"] = reason  # type: ignore[typeddict-item]
        state["status"] = "SUCCEEDED" if reason == "COMPLETED" else "FAILED"  # type: ignore[typeddict-item]
        state["observations"].append(_observation("system", summary, {"stop_reason": reason}))

    @staticmethod
    def _save_run(
        db: Session,
        state: AgentState,
        agent_name: str,
        *,
        status: str,
        finished_at: datetime | None = None,
    ) -> None:
        row = db.get(AgentRun, state["run_id"])
        if row is None:
            row = AgentRun(
                id=state["run_id"],
                agent_name=agent_name,
                trace_id=state["request"].trace_id,
                user_id=state["request"].user_id,
                region=state["request"].region,
                started_at=state["started_at"],
                model_version=None,
                prompt_version=PROMPT_VERSION,
            )
            db.add(row)
        row.status = status
        row.iterations = state.get("model_calls", 0) + state.get("tool_calls", 0)
        row.input_tokens = state.get("model_tokens", 0)  # type: ignore[arg-type]
        row.output_tokens = 0
        row.stop_reason = state.get("stop_reason")
        row.finished_at = finished_at
        db.commit()


def build_supervisor(model: SupervisorModel | None = None, settings: Settings | None = None) -> Supervisor:
    """Factory kept free of model-client initialization for API startup."""

    return Supervisor(model=model, settings=settings)
