"""Deterministic inspection scheduling and execution service."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import AuthPrincipal, ensure_region_access
from app.models.facility import Facility
from app.models.people import Technician
from app.models.work_order import InspectionTask
from app.schemas.work_order import InspectionCreate, InspectionStatusUpdate
from app.services.audit_service import record_security_event

INSPECTION_TRANSITIONS = {
    "SCHEDULED": {"ASSIGNED", "DEFERRED"},
    "ASSIGNED": {"IN_PROGRESS", "DEFERRED"},
    "IN_PROGRESS": {"DEFERRED", "COMPLETED"},
    "DEFERRED": {"IN_PROGRESS"},
    "COMPLETED": set(),
}


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message, "retryable": False})


def _permission(principal: AuthPrincipal, permission: str, request: Request) -> None:
    if not principal.has_permission(permission):
        record_security_event(
            "permission_denied", request=request, subject=principal.subject, details={"permission": permission}
        )
        raise _error(403, "PERMISSION_DENIED", "没有执行该操作的权限")


def inspection_dict(task: InspectionTask) -> dict:
    return {
        "id": task.id,
        "facility_id": task.facility_id,
        "area": task.area,
        "priority": task.priority,
        "scheduled_at": task.scheduled_at,
        "due_at": task.due_at,
        "completed_at": task.completed_at,
        "assignee_id": task.assignee_id,
        "status": task.status,
        "region": task.region,
        "source_type": task.source_type,
        "source_system": task.source_system,
        "result_notes": task.result_notes,
        "defer_reason": task.defer_reason,
        "version": task.version,
    }


def create_inspection(
    db: Session, principal: AuthPrincipal, request: Request, payload: InspectionCreate
) -> InspectionTask:
    _permission(principal, "inspection:create", request)
    facility = db.get(Facility, payload.facility_id) if payload.facility_id else None
    if payload.facility_id and (facility is None or facility.is_deleted):
        raise _error(404, "FACILITY_NOT_FOUND", "关联设施不存在")
    region = payload.region or (facility.region if facility else None)
    if region is None and "*" not in principal.regions and "admin" not in principal.roles:
        raise _error(422, "REGION_REQUIRED", "区域用户创建资源时必须提供区域或关联设施")
    ensure_region_access(principal, region, request)
    if facility is not None and payload.region and payload.region != facility.region:
        raise _error(422, "REGION_MISMATCH", "巡检区域必须与关联设施一致")
    now = datetime.now(UTC).replace(tzinfo=None)
    task = InspectionTask(
        id=f"INS-{uuid4().hex[:16].upper()}",
        facility_id=payload.facility_id,
        area=payload.area,
        priority=payload.priority,
        scheduled_at=payload.scheduled_at,
        due_at=payload.due_at,
        status="SCHEDULED",
        region=region,
        source_type="internal",
        source_system="municipal-facility-ops",
        data_version="step13-v1",
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    record_security_event(
        "inspection_created", request=request, subject=principal.subject, details={"inspection_id": task.id}
    )
    return task


def list_inspections(
    db: Session,
    principal: AuthPrincipal,
    request: Request,
    page: int,
    page_size: int,
    status: str | None,
    region: str | None,
) -> dict:
    _permission(principal, "inspection:read", request)
    ensure_region_access(principal, region, request)
    stmt = select(InspectionTask).where(InspectionTask.is_deleted.is_(False))
    if "*" not in principal.regions and "admin" not in principal.roles:
        stmt = stmt.where(
            InspectionTask.region.in_(sorted(principal.regions))
            if principal.regions
            else InspectionTask.id == "__none__"
        )
    if status:
        stmt = stmt.where(InspectionTask.status == status)
    if region:
        stmt = stmt.where(InspectionTask.region == region)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    tasks = db.scalars(
        stmt.order_by(InspectionTask.scheduled_at, InspectionTask.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {"items": [inspection_dict(task) for task in tasks], "total": total, "page": page, "page_size": page_size}


def get_inspection(
    db: Session,
    principal: AuthPrincipal,
    request: Request,
    task_id: str,
    required_permission: str | None = "inspection:read",
) -> InspectionTask:
    if required_permission:
        _permission(principal, required_permission, request)
    task = db.get(InspectionTask, task_id)
    if task is None or task.is_deleted:
        raise _error(404, "INSPECTION_NOT_FOUND", "巡检任务不存在")
    ensure_region_access(principal, task.region, request)
    return task


def assign_inspection(
    db: Session, principal: AuthPrincipal, request: Request, task_id: str, assignee_id: str
) -> InspectionTask:
    _permission(principal, "inspection:write", request)
    task = get_inspection(db, principal, request, task_id, required_permission=None)
    if task.status not in {"SCHEDULED", "ASSIGNED", "DEFERRED"}:
        raise _error(409, "INVALID_INSPECTION_ASSIGNMENT", "当前状态不允许派工")
    technician = db.get(Technician, assignee_id)
    if technician is None:
        raise _error(404, "TECHNICIAN_NOT_FOUND", "维修人员不存在")
    if not technician.active:
        raise _error(409, "TECHNICIAN_INACTIVE", "维修人员已停用")
    ensure_region_access(principal, technician.region, request)
    if task.region and technician.region and task.region != technician.region:
        raise _error(409, "ASSIGNEE_REGION_MISMATCH", "维修人员不属于巡检区域")
    task.assignee_id = assignee_id
    task.status = "ASSIGNED"
    task.version += 1
    task.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(task)
    record_security_event(
        "inspection_assigned",
        request=request,
        subject=principal.subject,
        details={"inspection_id": task.id, "assignee_id": assignee_id},
    )
    return task


def update_inspection_status(
    db: Session, principal: AuthPrincipal, request: Request, task_id: str, payload: InspectionStatusUpdate
) -> InspectionTask:
    _permission(principal, "inspection:write", request)
    task = get_inspection(db, principal, request, task_id, required_permission=None)
    if payload.status not in INSPECTION_TRANSITIONS.get(task.status, set()):
        raise _error(409, "INVALID_INSPECTION_TRANSITION", f"不允许从 {task.status} 变更到 {payload.status}")
    previous = task.status
    task.status = payload.status
    task.defer_reason = payload.reason if payload.status == "DEFERRED" else task.defer_reason
    task.result_notes = payload.result_notes or task.result_notes
    if payload.status == "COMPLETED":
        task.completed_at = datetime.now(UTC).replace(tzinfo=None)
    task.version += 1
    task.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(task)
    record_security_event(
        "inspection_status_changed",
        request=request,
        subject=principal.subject,
        details={"inspection_id": task.id, "from": previous, "to": payload.status},
    )
    return task
