from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.auth import AuthPrincipal, require_permission
from app.core.dependencies import get_db_session
from app.schemas.work_order import InspectionAssign, InspectionCreate, InspectionStatusUpdate
from app.services.inspection_service import (
    assign_inspection,
    create_inspection,
    get_inspection,
    inspection_dict,
    list_inspections,
    update_inspection_status,
)

router = APIRouter(prefix="/api/inspections", tags=["inspections"])


@router.post("", status_code=201)
def create(
    payload: InspectionCreate,
    request: Request,
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("inspection:create")),
) -> dict:
    return {"item": inspection_dict(create_inspection(db, principal, request, payload))}


@router.get("")
def list_route(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None, max_length=32),
    region: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("inspection:read")),
) -> dict:
    return list_inspections(db, principal, request, page, page_size, status, region)


@router.get("/{task_id}")
def detail(
    task_id: str,
    request: Request,
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("inspection:read")),
) -> dict:
    return {"item": inspection_dict(get_inspection(db, principal, request, task_id))}


@router.patch("/{task_id}/assign")
def assign(
    task_id: str,
    payload: InspectionAssign,
    request: Request,
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("inspection:write")),
) -> dict:
    return {"item": inspection_dict(assign_inspection(db, principal, request, task_id, payload.assignee_id))}


@router.patch("/{task_id}/status")
def update_status(
    task_id: str,
    payload: InspectionStatusUpdate,
    request: Request,
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("inspection:write")),
) -> dict:
    return {"item": inspection_dict(update_inspection_status(db, principal, request, task_id, payload))}
