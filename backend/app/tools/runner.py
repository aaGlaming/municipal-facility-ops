"""Validated execution gateway for Agent tools."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, Request
from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import AuthPrincipal, ensure_region_access
from app.core.config import Settings, get_settings
from app.models.people import Technician, Vendor
from app.models.tool_call import ToolCall
from app.schemas.agent import ToolCallRequest, ToolCallResult, ToolFailure
from app.schemas.facility import ReportCreate
from app.schemas.rag import RagSearchRequest
from app.schemas.work_order import (
    AcceptanceCreate,
    InspectionCreate,
    InspectionStatusUpdate,
    WorkOrderCreate,
    WorkOrderStatusUpdate,
)
from app.services import facility_service, inspection_service, work_order_service
from app.services.audit_service import record_security_event
from app.services.retrieval_service import search_documents
from app.tools.contracts import (
    AGENT_TOOL_WHITELIST,
    TOOL_CONTRACTS,
    SafetyChecklistInput,
    StaffCapacityInput,
)


def _failure(call: ToolCallRequest, code: str, message: str, retryable: bool = False, **details: Any) -> ToolCallResult:
    return ToolCallResult(
        tool_call_id=call.tool_call_id,
        tool_name=call.tool_name,
        status="FAILED",
        idempotency_key=call.idempotency_key,
        error=ToolFailure(code=code, message=message, retryable=retryable, details=details),
    )


def _record_audit(
    call: ToolCallRequest, principal: AuthPrincipal, request: Request, status: str, **details: Any
) -> None:
    record_security_event(
        "agent_tool_call",
        request=request,
        subject=principal.subject,
        details={
            "agent_run_id": call.agent_run_id,
            "tool_call_id": call.tool_call_id,
            "tool_name": call.tool_name,
            "agent_name": call.agent_name,
            "idempotency_key": call.idempotency_key,
            "status": status,
            **details,
        },
    )


def _serialize(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    return value


def _persist_new_call(
    db: Session, call: ToolCallRequest, risk_level: str, action: str, arguments: dict[str, Any]
) -> tuple[ToolCall | None, bool]:
    existing = db.scalar(
        select(ToolCall).where(
            ToolCall.agent_run_id == call.agent_run_id,
            ToolCall.idempotency_key == call.idempotency_key,
        )
    )
    if existing is not None:
        return existing, False
    row = ToolCall(
        id=call.tool_call_id,
        agent_run_id=call.agent_run_id,
        tool_name=call.tool_name,
        action=action,
        risk_level=risk_level,
        status="RUNNING",
        idempotency_key=call.idempotency_key,
        request_json=arguments,
        human_confirmation=call.human_confirmation,
        started_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return db.scalar(
            select(ToolCall).where(
                ToolCall.agent_run_id == call.agent_run_id,
                ToolCall.idempotency_key == call.idempotency_key,
            )
        ), False
    return row, True


def _duplicate_result(call: ToolCallRequest, row: ToolCall) -> ToolCallResult:
    response = row.response_json if isinstance(row.response_json, dict) else {}
    return ToolCallResult(
        tool_call_id=call.tool_call_id,
        tool_name=call.tool_name,
        status="DUPLICATE",
        result=response.get("result", {}),
        error=ToolFailure(**response["error"]) if isinstance(response.get("error"), dict) else None,
        idempotency_key=call.idempotency_key,
        duplicate_of=row.id,
    )


def _finish_call(db: Session, row: ToolCall, result: ToolCallResult) -> None:
    row.status = result.status
    row.response_json = result.model_dump(mode="json")
    row.error = result.error.message if result.error else None
    row.finished_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()


def _validate_access(
    principal: AuthPrincipal, call: ToolCallRequest, contract: Any, *, check_confirmation: bool = True
) -> ToolCallResult | None:
    if call.agent_name not in contract.allowed_agents or call.tool_name not in AGENT_TOOL_WHITELIST.get(
        call.agent_name, ()
    ):
        return _failure(call, "TOOL_NOT_ALLOWED", "当前 Agent 不在该工具白名单中")
    if not all(principal.has_permission(permission) for permission in contract.permissions):
        return _failure(call, "PERMISSION_DENIED", "当前用户没有工具所需权限")
    if check_confirmation and contract.confirmation == "REQUIRED" and not call.human_confirmation:
        return ToolCallResult(
            tool_call_id=call.tool_call_id,
            tool_name=call.tool_name,
            status="PENDING_CONFIRMATION",
            idempotency_key=call.idempotency_key,
            error=ToolFailure(
                code="HUMAN_CONFIRMATION_REQUIRED",
                message="该高风险工具需要人工确认后才能执行",
                retryable=False,
            ),
        )
    return None


def _items_from_capacity(
    db: Session, principal: AuthPrincipal, request: Request, payload: StaffCapacityInput
) -> dict[str, Any]:
    ensure_region_access(principal, payload.region, request)
    technicians = db.scalars(
        select(Technician).where(Technician.region == payload.region, Technician.active.is_(True)).limit(100)
    ).all()
    vendors = db.scalars(
        select(Vendor).where(Vendor.region == payload.region, Vendor.active.is_(True)).limit(100)
    ).all()
    items = [
        {"id": technician.id, "name": technician.name, "kind": "technician", "region": technician.region}
        for technician in technicians
    ]
    items.extend(
        {"id": vendor.id, "name": vendor.name, "kind": "vendor", "region": vendor.region} for vendor in vendors
    )
    return {"items": items, "total": len(items)}


def _safety_result(payload: SafetyChecklistInput) -> dict[str, Any]:
    rules = [
        "确认现场边界并设置行人/车辆警示",
        "维修前核对断电、隔离和许可要求",
        "按设施类型佩戴匹配的 PPE",
        "完成前不得移除临时防护或恢复危险设备",
    ]
    if payload.facility_type in {"traffic_signal", "road_damage"}:
        rules.insert(0, "先设置交通导流和作业区隔离")
    return {"recommendations": [{"type": "safety", "text": item} for item in rules], "evidence": []}


def _execute(
    db: Session,
    settings: Settings,
    principal: AuthPrincipal,
    request: Request,
    call: ToolCallRequest,
    payload: BaseModel,
) -> dict[str, Any]:
    name = call.tool_name
    if name == "facility.search":
        data = payload.model_dump()
        if data.get("facility_id"):
            return {"items": [facility_service.get_facility(db, principal, request, data["facility_id"])], "total": 1}
        return facility_service.list_facilities(
            db,
            principal,
            request,
            data["page"],
            data["page_size"],
            data.get("facility_type"),
            None,
            data.get("region"),
            None,
            data.get("query"),
        )
    if name == "facility.history":
        data = payload.model_dump()
        return facility_service.list_facility_events(db, principal, request, data["facility_id"], 1, data["limit"])
    if name == "rag.search":
        result = search_documents(db, settings, principal, request, RagSearchRequest(**payload.model_dump()))
        return {"recommendations": result["items"], "evidence": [item["metadata"] for item in result["items"]]}
    if name == "sla.calculate":
        data = payload.model_dump()
        minutes = work_order_service.SLA_MINUTES[data["priority"]]
        due_at = data["reported_at"] + timedelta(minutes=minutes)
        return {"item": {"priority": data["priority"], "resolution_due_at": due_at, "sla_minutes": minutes}}
    if name == "staff.capacity":
        return _items_from_capacity(db, principal, request, payload)  # type: ignore[arg-type]
    if name == "report.create":
        data = payload.model_dump()
        report, created, duplicate_of = facility_service.create_report(
            db,
            principal,
            request,
            ReportCreate(
                description=data["description"],
                category=data["issue_type"],
                facility_id=data.get("facility_id"),
                region=data["region"],
                source="agent",
                idempotency_key=call.idempotency_key,
                latitude=data.get("latitude"),
                longitude=data.get("longitude"),
            ),
        )
        return {
            "resource_id": report.id,
            "status": report.status,
            "duplicate": not created,
            "duplicate_of": duplicate_of,
        }
    if name == "inspection.create":
        data = payload.model_dump()
        task = inspection_service.create_inspection(
            db,
            principal,
            request,
            InspectionCreate(
                facility_id=data["facility_id"],
                region=data["region"],
                priority=data["priority"],
                scheduled_at=data["scheduled_at"],
                due_at=data["due_at"],
            ),
        )
        return {"resource_id": task.id, "status": task.status, "duplicate": False}
    if name == "inspection.assign":
        data = payload.model_dump()
        task = inspection_service.assign_inspection(db, principal, request, data["inspection_id"], data["assignee_id"])
        return {"resource_id": task.id, "status": task.status, "duplicate": False}
    if name == "inspection.update_status":
        data = payload.model_dump()
        task = inspection_service.update_inspection_status(
            db,
            principal,
            request,
            data["inspection_id"],
            InspectionStatusUpdate(
                status=data["target_status"], reason=data.get("reason"), result_notes=data.get("result_notes")
            ),
        )
        return {"resource_id": task.id, "status": task.status, "duplicate": False}
    if name == "work_order.create":
        data = payload.model_dump()
        order, created = work_order_service.create_work_order(
            db,
            principal,
            request,
            WorkOrderCreate(
                facility_id=data["facility_id"],
                report_id=data.get("report_id"),
                priority=data["priority"],
                problem_type=data["summary"],
                region=data["region"],
                idempotency_key=call.idempotency_key,
            ),
        )
        return {"resource_id": order.id, "status": order.status, "duplicate": not created}
    if name == "work_order.assign":
        data = payload.model_dump()
        order = work_order_service.get_work_order(db, principal, request, data["work_order_id"], "work_order:write")
        if order.status != "TRIAGED":
            raise HTTPException(
                status_code=409,
                detail={"code": "INVALID_STATE_TRANSITION", "message": "只有 TRIAGED 工单可以派工", "retryable": False},
            )
        updated, _ = work_order_service.update_work_order_status(
            db,
            principal,
            request,
            order.id,
            WorkOrderStatusUpdate(
                status="ASSIGNED",
                idempotency_key=call.idempotency_key,
                assignee_id=data.get("assignee_id"),
                vendor_id=data.get("vendor_id"),
                human_confirmation=call.human_confirmation,
            ),
        )
        return {"resource_id": updated.id, "status": updated.status, "duplicate": False}
    if name == "work_order.escalate_overdue":
        data = payload.model_dump()
        ensure_region_access(principal, data.get("region"), request)
        return {"escalated_count": work_order_service.escalate_overdue(db, principal, request)}
    if name == "work_order.update_status":
        data = payload.model_dump()
        updated, changed = work_order_service.update_work_order_status(
            db,
            principal,
            request,
            data["work_order_id"],
            WorkOrderStatusUpdate(
                status=data["target_status"],
                idempotency_key=call.idempotency_key,
                handling_notes=data.get("reason"),
                human_confirmation=call.human_confirmation,
            ),
        )
        return {"resource_id": updated.id, "status": updated.status, "duplicate": not changed}
    if name == "safety.checklist":
        return _safety_result(payload)  # type: ignore[arg-type]
    if name == "acceptance.submit":
        data = payload.model_dump()
        order = work_order_service.accept_work_order(
            db,
            principal,
            request,
            data["work_order_id"],
            AcceptanceCreate(result=data["result"], reason=data.get("reason"), evidence_uri=data.get("evidence_uri")),
        )
        return {"resource_id": order.id, "status": order.status, "duplicate": False}
    if name == "audit.record":
        data = payload.model_dump()
        audit_id = f"AUD-{uuid4().hex[:16].upper()}"
        record_security_event(
            data["action"],
            request=request,
            subject=principal.subject,
            details={
                "audit_id": audit_id,
                "resource_type": data["resource_type"],
                "resource_id": data.get("resource_id"),
                "result": data["result"],
            },
        )
        return {"audit_id": audit_id, "recorded": True}
    raise ValueError(f"tool implementation missing: {name}")


def execute_tool(
    db: Session,
    principal: AuthPrincipal,
    request: Request,
    call: ToolCallRequest,
    settings: Settings | None = None,
) -> ToolCallResult:
    """Validate and execute one tool call, returning a machine-readable result."""

    runtime_settings = settings or get_settings()
    contract = TOOL_CONTRACTS.get(call.tool_name)
    if contract is None:
        result = _failure(call, "TOOL_NOT_FOUND", "工具未注册")
        _record_audit(call, principal, request, result.status, error_code="TOOL_NOT_FOUND")
        return result
    access_error = _validate_access(principal, call, contract, check_confirmation=False)
    if access_error is not None:
        _record_audit(
            call,
            principal,
            request,
            access_error.status,
            error_code=access_error.error.code if access_error.error else None,
        )
        return access_error
    try:
        payload = contract.input_model.model_validate(call.arguments)
    except ValidationError as exc:
        fields = sorted({".".join(str(part) for part in error["loc"]) for error in exc.errors()})
        result = _failure(call, "INVALID_ARGUMENT", "工具参数校验失败", fields=fields)
        _record_audit(call, principal, request, result.status, error_code="INVALID_ARGUMENT")
        return result

    row, created = _persist_new_call(db, call, contract.risk_level, contract.audit_action, _serialize(payload))
    if row is None:
        result = _failure(call, "IDEMPOTENCY_UNAVAILABLE", "无法建立幂等记录", retryable=True)
        _record_audit(call, principal, request, result.status, error_code="IDEMPOTENCY_UNAVAILABLE")
        return result
    if not created and row.status == "RUNNING":
        result = _failure(call, "TOOL_IN_PROGRESS", "相同幂等键的工具调用仍在执行", retryable=True)
        _record_audit(call, principal, request, result.status, error_code="TOOL_IN_PROGRESS")
        return result
    if not created:
        if row.tool_name != call.tool_name:
            result = _failure(call, "IDEMPOTENCY_KEY_CONFLICT", "幂等键已经用于其他工具")
            _record_audit(call, principal, request, result.status, error_code="IDEMPOTENCY_KEY_CONFLICT")
            return result
        if row.status == "PENDING_CONFIRMATION" and call.human_confirmation:
            row.status = "RUNNING"
            row.human_confirmation = True
            row.error = None
            db.commit()
        else:
            result = _duplicate_result(call, row)
            _record_audit(call, principal, request, result.status, duplicate_of=row.id)
            return result
    if contract.confirmation == "REQUIRED" and not call.human_confirmation:
        result = _validate_access(principal, call, contract)
        assert result is not None
        _finish_call(db, row, result)
        _record_audit(call, principal, request, result.status, error_code="HUMAN_CONFIRMATION_REQUIRED")
        return result
    try:
        raw_result = _execute(db, runtime_settings, principal, request, call, payload)
        validated_result = contract.output_model.model_validate(raw_result)
        result = ToolCallResult(
            tool_call_id=call.tool_call_id,
            tool_name=call.tool_name,
            status="SUCCEEDED",
            result=validated_result.model_dump(mode="json"),
            idempotency_key=call.idempotency_key,
        )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        result = _failure(
            call,
            str(detail.get("code", "TOOL_EXECUTION_FAILED")),
            str(detail.get("message", "工具执行失败")),
            bool(detail.get("retryable", False)),
        )
    except Exception:
        result = _failure(call, "TOOL_EXECUTION_FAILED", "工具执行失败", retryable=True)
    _finish_call(db, row, result)
    _record_audit(call, principal, request, result.status, error_code=result.error.code if result.error else None)
    return result
