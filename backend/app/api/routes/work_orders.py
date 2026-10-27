from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.core.auth import AuthPrincipal, require_permission
from app.core.dependencies import get_db_session
from app.schemas.work_order import AcceptanceCreate, WorkOrderCreate, WorkOrderStatusUpdate
from app.services.work_order_service import (
    accept_work_order,
    create_work_order,
    escalate_overdue,
    get_work_order,
    list_work_orders,
    update_work_order_status,
    work_order_dict,
)

router = APIRouter(prefix="/api/work-orders", tags=["work-orders"])


@router.post("", status_code=201)
def create(
    payload: WorkOrderCreate,
    request: Request,
    response: Response,
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("work_order:create")),
) -> dict:
    order, created = create_work_order(db, principal, request, payload)
    if not created:
        response.status_code = 200
    return {"item": work_order_dict(order), "created": created}


@router.post("/escalate-overdue")
def escalate(
    request: Request,
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("work_order:write")),
) -> dict:
    return {"escalated": escalate_overdue(db, principal, request)}


@router.get("")
def list_route(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None, max_length=32),
    region: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("work_order:read")),
) -> dict:
    return list_work_orders(db, principal, request, page, page_size, status, region)


@router.get("/{work_order_id}")
def detail(
    work_order_id: str,
    request: Request,
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("work_order:read")),
) -> dict:
    return {"item": work_order_dict(get_work_order(db, principal, request, work_order_id))}


@router.post("/{work_order_id}/status")
def update_status(
    work_order_id: str,
    payload: WorkOrderStatusUpdate,
    request: Request,
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("work_order:write")),
) -> dict:
    order, _changed = update_work_order_status(db, principal, request, work_order_id, payload)
    return {"item": work_order_dict(order), "idempotency_key": payload.idempotency_key}


@router.post("/{work_order_id}/acceptance")
def acceptance(
    work_order_id: str,
    payload: AcceptanceCreate,
    request: Request,
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("work_order:accept")),
) -> dict:
    return {"item": work_order_dict(accept_work_order(db, principal, request, work_order_id, payload))}
