"""Controlled Agent run endpoints used by the Step26 workbench."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.auth import AuthPrincipal, require_permission
from app.schemas.agent import AgentObservation, AgentResponse, HumanConfirmation
from app.schemas.agent_interaction import AgentDecisionAction, AgentRunAction, AgentRunCreate

router = APIRouter(prefix="/api/agents", tags=["agents"])
_RUNS: dict[str, dict[str, Any]] = {}


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _view(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key != "owner"}


def _owned(run_id: str, principal: AuthPrincipal) -> dict[str, Any]:
    record = _RUNS.get(run_id)
    if record is None:
        raise HTTPException(
            status_code=404, detail={"code": "AGENT_RUN_NOT_FOUND", "message": f"运行记录不存在：{run_id}"}
        )
    if record["owner"] != principal.subject and "admin" not in principal.roles and "*" not in principal.permissions:
        raise HTTPException(
            status_code=403, detail={"code": "AGENT_RUN_SCOPE_DENIED", "message": "无权访问该 Agent 运行"}
        )
    return record


@router.post("/runs", status_code=201)
def create_run(
    payload: AgentRunCreate, request: Request, principal: AuthPrincipal = Depends(require_permission("agent:run"))
) -> dict[str, Any]:
    run_id = f"RUN-{uuid4().hex[:16].upper()}"
    trace_id = getattr(request.state, "trace_id", str(uuid4()))
    high_risk = any(
        word in f"{payload.intent} {payload.description}".casefold()
        for word in ("安全", "派工", "验收", "封路", "带电", "close", "dispatch")
    )
    observations = [
        AgentObservation(
            observation_id=f"OBS-{uuid4().hex[:12].upper()}",
            source="system",
            summary="已接收报修，正在进行问题分诊和设施识别",
            data={"phase": "triage", "attachment_count": len(payload.attachments)},
            created_at=_now(),
        )
    ]
    pending = (
        HumanConfirmation(
            confirmation_id=f"CONF-{uuid4().hex[:12].upper()}",
            action="agent_high_risk_action",
            summary="该请求可能触发高风险或不可逆工单动作，需要授权人员确认",
            risk_level="HIGH",
            requested_at=_now(),
        )
        if high_risk
        else None
    )
    response = AgentResponse(
        agent_run_id=run_id,
        trace_id=trace_id,
        status="WAITING_CONFIRMATION" if pending else "SUCCEEDED",
        stop_reason="HUMAN_CONFIRMATION_REQUIRED" if pending else "COMPLETED",
        answer=None if pending else "已完成分诊建议，后续可进入工单调度。",
        observations=observations,
        pending_confirmation=pending,
    )
    record = {
        "owner": principal.subject,
        "agent_run_id": run_id,
        "trace_id": trace_id,
        "status": response.status,
        "phase": "waiting_confirmation" if pending else "completed",
        "created_at": _now(),
        "request": payload.model_dump(mode="json"),
        "response": response.model_dump(mode="json"),
        "tool_trace": [],
        "work_order": None,
    }
    _RUNS[run_id] = record
    return _view(record)


@router.get("/runs/{run_id}")
def get_run(run_id: str, principal: AuthPrincipal = Depends(require_permission("agent:run"))) -> dict[str, Any]:
    return _view(_owned(run_id, principal))


@router.get("/runs/{run_id}/trace")
def get_trace(run_id: str, principal: AuthPrincipal = Depends(require_permission("agent:run"))) -> dict[str, Any]:
    record = _owned(run_id, principal)
    return {
        "agent_run_id": run_id,
        "trace_id": record["trace_id"],
        "events": record["tool_trace"],
        "observations": record["response"].get("observations", []),
    }


@router.post("/runs/{run_id}/confirmation")
def decide_confirmation(
    run_id: str, payload: AgentDecisionAction, principal: AuthPrincipal = Depends(require_permission("agent:run"))
) -> dict[str, Any]:
    record = _owned(run_id, principal)
    if record["status"] != "WAITING_CONFIRMATION":
        raise HTTPException(
            status_code=409, detail={"code": "CONFIRMATION_NOT_PENDING", "message": "当前运行没有待确认动作"}
        )
    response = AgentResponse.model_validate(record["response"])
    approved = payload.decision == "approve"
    response.status = "SUCCEEDED" if approved else "CANCELLED"
    response.stop_reason = "COMPLETED" if approved else "CANCELLED"
    response.answer = "人工确认已通过，建议可继续执行。" if approved else "人工已拒绝该动作。"
    response.pending_confirmation = None
    response.observations.append(
        AgentObservation(
            observation_id=f"OBS-{uuid4().hex[:12].upper()}",
            source="human",
            summary=response.answer,
            data={"decision": payload.decision, "reason": payload.reason},
            created_at=_now(),
        )
    )
    record["status"] = response.status
    record["phase"] = "completed" if approved else "cancelled"
    record["response"] = response.model_dump(mode="json")
    record["tool_trace"].append(
        {
            "type": "human_confirmation",
            "decision": payload.decision,
            "reason": payload.reason,
            "created_at": _now().isoformat(),
        }
    )
    return _view(record)


@router.post("/runs/{run_id}/cancel")
def cancel_run(
    run_id: str, payload: AgentRunAction, principal: AuthPrincipal = Depends(require_permission("agent:run"))
) -> dict[str, Any]:
    record = _owned(run_id, principal)
    response = AgentResponse.model_validate(record["response"])
    response.status = "CANCELLED"
    response.stop_reason = "CANCELLED"
    response.answer = payload.reason or "运行已取消。"
    response.pending_confirmation = None
    record["status"] = "CANCELLED"
    record["phase"] = "cancelled"
    record["response"] = response.model_dump(mode="json")
    return _view(record)


@router.post("/runs/{run_id}/retry", status_code=201)
def retry_run(run_id: str, principal: AuthPrincipal = Depends(require_permission("agent:run"))) -> dict[str, Any]:
    source = _owned(run_id, principal)
    request_payload = AgentRunCreate.model_validate(source["request"])
    request_payload.intent = f"重试：{request_payload.intent}"
    new_id = f"RUN-{uuid4().hex[:16].upper()}"
    trace_id = str(uuid4())
    response = AgentResponse(
        agent_run_id=new_id,
        trace_id=trace_id,
        status="SUCCEEDED",
        stop_reason="COMPLETED",
        answer="已创建重试运行。",
        observations=[],
    )
    record = {
        "owner": principal.subject,
        "agent_run_id": new_id,
        "trace_id": trace_id,
        "status": response.status,
        "phase": "completed",
        "created_at": _now(),
        "request": request_payload.model_dump(mode="json"),
        "response": response.model_dump(mode="json"),
        "tool_trace": [{"type": "retry", "retry_of": run_id, "created_at": _now().isoformat()}],
        "work_order": None,
    }
    _RUNS[new_id] = record
    return _view(record)
