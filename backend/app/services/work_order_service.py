"""Deterministic work-order state, SLA and acceptance services."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import AuthPrincipal, ensure_region_access, require_human_confirmation
from app.models.facility import CitizenReport, Facility
from app.models.people import Technician, Vendor
from app.models.work_order import AcceptanceRecord, WorkOrder, WorkOrderStatusEvent
from app.schemas.work_order import AcceptanceCreate, WorkOrderCreate, WorkOrderStatusUpdate
from app.services.audit_service import record_security_event

WORK_ORDER_TRANSITIONS: dict[str, set[str]] = {
    "NEW": {"TRIAGED", "CANCELLED", "ESCALATED"},
    "TRIAGED": {"ASSIGNED", "BLOCKED", "ESCALATED", "CANCELLED"},
    "ASSIGNED": {"IN_PROGRESS", "CANCELLED", "BLOCKED"},
    "IN_PROGRESS": {"WAITING_CONFIRMATION", "BLOCKED", "ESCALATED"},
    "WAITING_CONFIRMATION": {"COMPLETED", "REJECTED"},
    "COMPLETED": {"ACCEPTED", "REJECTED"},
    "ACCEPTED": {"CLOSED", "REJECTED"},
    "REJECTED": {"IN_PROGRESS", "CANCELLED"},
    "BLOCKED": {"IN_PROGRESS", "ESCALATED", "CANCELLED"},
    "ESCALATED": {"ASSIGNED", "CANCELLED"},
    "CANCELLED": set(),
    "CLOSED": set(),
}
SLA_MINUTES = {"P1": 4 * 60, "P2": 24 * 60, "P3": 3 * 24 * 60, "P4": 7 * 24 * 60}


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message, "retryable": False})


def _permission(principal: AuthPrincipal, permission: str, request: Request) -> None:
    if not principal.has_permission(permission):
        record_security_event(
            "permission_denied", request=request, subject=principal.subject, details={"permission": permission}
        )
        raise _error(403, "PERMISSION_DENIED", "没有执行该操作的权限")


def _validate_assignee(
    db: Session, principal: AuthPrincipal, request: Request, assignee_id: str | None, region: str | None
) -> None:
    if assignee_id is None:
        return
    technician = db.get(Technician, assignee_id)
    if technician is None:
        raise _error(404, "TECHNICIAN_NOT_FOUND", "维修人员不存在")
    if not technician.active:
        raise _error(409, "TECHNICIAN_INACTIVE", "维修人员已停用")
    ensure_region_access(principal, technician.region, request)
    if region and technician.region and technician.region != region:
        raise _error(409, "ASSIGNEE_REGION_MISMATCH", "维修人员不属于工单区域")


def _validate_vendor(
    db: Session, principal: AuthPrincipal, request: Request, vendor_id: str | None, region: str | None
) -> None:
    if vendor_id is None:
        return
    vendor = db.get(Vendor, vendor_id)
    if vendor is None:
        raise _error(404, "VENDOR_NOT_FOUND", "供应商不存在")
    if not vendor.active:
        raise _error(409, "VENDOR_INACTIVE", "供应商已停用")
    ensure_region_access(principal, vendor.region, request)
    if region and vendor.region and vendor.region != region:
        raise _error(409, "VENDOR_REGION_MISMATCH", "供应商不属于工单区域")


def work_order_dict(order: WorkOrder) -> dict:
    return {
        "id": order.id,
        "report_id": order.report_id,
        "facility_id": order.facility_id,
        "priority": order.priority,
        "problem_type": order.problem_type,
        "assignee_id": order.assignee_id,
        "vendor_id": order.vendor_id,
        "due_at": order.due_at,
        "completed_at": order.completed_at,
        "status": order.status,
        "idempotency_key": order.idempotency_key,
        "region": order.region,
        "source_type": order.source_type,
        "source_system": order.source_system,
        "data_version": order.data_version,
        "version": order.version,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }


def create_work_order(
    db: Session, principal: AuthPrincipal, request: Request, payload: WorkOrderCreate
) -> tuple[WorkOrder, bool]:
    _permission(principal, "work_order:create", request)
    existing = db.scalar(select(WorkOrder).where(WorkOrder.idempotency_key == payload.idempotency_key))
    if existing is not None:
        ensure_region_access(principal, existing.region, request)
        return existing, False
    facility = db.get(Facility, payload.facility_id) if payload.facility_id else None
    if payload.facility_id and (facility is None or facility.is_deleted):
        raise _error(404, "FACILITY_NOT_FOUND", "关联设施不存在")
    if payload.report_id:
        report = db.get(CitizenReport, payload.report_id)
        if report is None or report.is_deleted:
            raise _error(404, "REPORT_NOT_FOUND", "关联问题上报不存在")
    region = payload.region or (facility.region if facility else None)
    if region is None and "*" not in principal.regions and "admin" not in principal.roles:
        raise _error(422, "REGION_REQUIRED", "区域用户创建资源时必须提供区域或关联设施")
    ensure_region_access(principal, region, request)
    if facility is not None and payload.region and payload.region != facility.region:
        raise _error(422, "REGION_MISMATCH", "工单区域必须与关联设施一致")
    _validate_assignee(db, principal, request, payload.assignee_id, region)
    _validate_vendor(db, principal, request, payload.vendor_id, region)
    now = datetime.now(UTC).replace(tzinfo=None)
    order = WorkOrder(
        id=f"WO-{uuid4().hex[:16].upper()}",
        report_id=payload.report_id,
        facility_id=payload.facility_id,
        priority=payload.priority,
        problem_type=payload.problem_type,
        assignee_id=payload.assignee_id,
        vendor_id=payload.vendor_id,
        due_at=payload.due_at or now + timedelta(minutes=SLA_MINUTES[payload.priority]),
        status="NEW",
        idempotency_key=payload.idempotency_key,
        region=region,
        source_type="internal",
        source_system="municipal-facility-ops",
        data_version="step13-v1",
        created_at=now,
        updated_at=now,
    )
    db.add(order)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(WorkOrder).where(WorkOrder.idempotency_key == payload.idempotency_key))
        if existing is not None:
            ensure_region_access(principal, existing.region, request)
            return existing, False
        raise
    db.refresh(order)
    record_security_event(
        "work_order_created", request=request, subject=principal.subject, details={"work_order_id": order.id}
    )
    return order, True


def list_work_orders(
    db: Session,
    principal: AuthPrincipal,
    request: Request,
    page: int,
    page_size: int,
    status: str | None,
    region: str | None,
) -> dict:
    _permission(principal, "work_order:read", request)
    ensure_region_access(principal, region, request)
    stmt = select(WorkOrder).where(WorkOrder.is_deleted.is_(False))
    if "*" not in principal.regions and "admin" not in principal.roles:
        stmt = stmt.where(
            WorkOrder.region.in_(sorted(principal.regions)) if principal.regions else WorkOrder.id == "__none__"
        )
    if status:
        stmt = stmt.where(WorkOrder.status == status)
    if region:
        stmt = stmt.where(WorkOrder.region == region)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.scalars(
        stmt.order_by(WorkOrder.created_at.desc(), WorkOrder.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {"items": [work_order_dict(order) for order in rows], "total": total, "page": page, "page_size": page_size}


def get_work_order(
    db: Session,
    principal: AuthPrincipal,
    request: Request,
    order_id: str,
    required_permission: str | None = "work_order:read",
) -> WorkOrder:
    if required_permission:
        _permission(principal, required_permission, request)
    order = db.get(WorkOrder, order_id)
    if order is None or order.is_deleted:
        raise _error(404, "WORK_ORDER_NOT_FOUND", "工单不存在")
    ensure_region_access(principal, order.region, request)
    return order


def authorize_work_order_update(
    principal: AuthPrincipal,
    work_order: WorkOrder | dict,
    requested_status: str,
    human_confirmation: bool,
    request: Request,
) -> None:
    if not principal.has_permission("work_order:write"):
        raise _error(403, "PERMISSION_DENIED", "没有执行该操作的权限")
    ensure_region_access(
        principal,
        getattr(work_order, "region", None) if not isinstance(work_order, dict) else work_order.get("region"),
        request,
    )
    if requested_status == "CLOSED":
        require_human_confirmation(principal, "close_work_order", human_confirmation, request)


def update_work_order_status(
    db: Session,
    principal: AuthPrincipal,
    request: Request,
    order_id: str,
    payload: WorkOrderStatusUpdate,
) -> tuple[WorkOrder, bool]:
    _permission(principal, "work_order:write", request)
    order = get_work_order(db, principal, request, order_id, required_permission=None)
    authorize_work_order_update(principal, order, payload.status, payload.human_confirmation, request)
    existing_event = db.scalar(
        select(WorkOrderStatusEvent).where(WorkOrderStatusEvent.idempotency_key == payload.idempotency_key)
    )
    if existing_event is not None:
        if existing_event.work_order_id != order.id:
            raise _error(409, "IDEMPOTENCY_KEY_CONFLICT", "幂等键已用于其他工单")
        return order, False
    if payload.idempotency_key == order.idempotency_key:
        return order, False
    if payload.status not in WORK_ORDER_TRANSITIONS.get(order.status, set()):
        raise _error(409, "INVALID_STATE_TRANSITION", f"不允许从 {order.status} 变更到 {payload.status}")
    if payload.assignee_id is not None:
        _validate_assignee(db, principal, request, payload.assignee_id, order.region)
        order.assignee_id = payload.assignee_id
    if payload.vendor_id is not None:
        _validate_vendor(db, principal, request, payload.vendor_id, order.region)
        order.vendor_id = payload.vendor_id
    if payload.status == "COMPLETED":
        order.completed_at = datetime.now(UTC).replace(tzinfo=None)
    previous = order.status
    order.status = payload.status
    order.version += 1
    order.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.add(
        WorkOrderStatusEvent(
            work_order_id=order.id,
            idempotency_key=payload.idempotency_key,
            from_status=previous,
            to_status=payload.status,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )
    if payload.handling_notes or payload.evidence_uri:
        db.add(
            AcceptanceRecord(
                id=f"ACC-{uuid4().hex[:16].upper()}",
                work_order_id=order.id,
                result="EVIDENCE_SUBMITTED",
                reason=payload.handling_notes,
                evidence_uri=payload.evidence_uri,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_event = db.scalar(
            select(WorkOrderStatusEvent).where(WorkOrderStatusEvent.idempotency_key == payload.idempotency_key)
        )
        if existing_event is not None and existing_event.work_order_id == order.id:
            return db.get(WorkOrder, order.id), False  # type: ignore[return-value]
        raise
    db.refresh(order)
    record_security_event(
        "work_order_status_changed",
        request=request,
        subject=principal.subject,
        details={"work_order_id": order.id, "from": previous, "to": payload.status},
    )
    return order, True


def accept_work_order(
    db: Session, principal: AuthPrincipal, request: Request, order_id: str, payload: AcceptanceCreate
) -> WorkOrder:
    _permission(principal, "work_order:accept", request)
    order = get_work_order(db, principal, request, order_id, required_permission=None)
    if order.status != "COMPLETED":
        raise _error(409, "ACCEPTANCE_NOT_READY", "只有已完成工单才能验收")
    result = AcceptanceRecord(
        id=f"ACC-{uuid4().hex[:16].upper()}",
        work_order_id=order.id,
        result=payload.result,
        reason=payload.reason,
        evidence_uri=payload.evidence_uri,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(result)
    order.status = payload.result if payload.result == "ACCEPTED" else "REJECTED"
    order.version += 1
    order.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(order)
    record_security_event(
        "work_order_accepted",
        request=request,
        subject=principal.subject,
        details={"work_order_id": order.id, "result": payload.result},
    )
    return order


def escalate_overdue(db: Session, principal: AuthPrincipal, request: Request) -> int:
    _permission(principal, "work_order:write", request)
    now = datetime.now(UTC).replace(tzinfo=None)
    stmt = select(WorkOrder).where(
        WorkOrder.due_at.is_not(None),
        WorkOrder.due_at < now,
        WorkOrder.status.not_in(("CLOSED", "CANCELLED", "ACCEPTED", "REJECTED", "ESCALATED")),
        WorkOrder.is_deleted.is_(False),
    )
    if "*" not in principal.regions and "admin" not in principal.roles:
        stmt = stmt.where(
            WorkOrder.region.in_(sorted(principal.regions)) if principal.regions else WorkOrder.id == "__none__"
        )
    orders = db.scalars(stmt).all()
    for order in orders:
        previous = order.status
        order.status = "ESCALATED"
        order.version += 1
        order.updated_at = now
        db.add(
            WorkOrderStatusEvent(
                work_order_id=order.id,
                idempotency_key=f"sla-escalation:{order.id}:{order.version}",
                from_status=previous,
                to_status="ESCALATED",
                created_at=now,
            )
        )
    db.commit()
    for order in orders:
        record_security_event(
            "work_order_sla_escalated", request=request, subject=principal.subject, details={"work_order_id": order.id}
        )
    return len(orders)
