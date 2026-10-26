from fastapi import APIRouter, HTTPException, Request

from app.schemas.common import StatusUpdateRequest

router = APIRouter(prefix="/api/work-orders", tags=["work-orders"])

WORK_ORDERS = {
    "WO-000001": {"id": "WO-000001", "status": "NEW", "source_type": "synthetic"},
}
IDEMPOTENCY_RESULTS: dict[str, dict] = {}
ALLOWED_TRANSITIONS = {
    "NEW": {"TRIAGED", "CANCELLED"},
    "TRIAGED": {"ASSIGNED", "BLOCKED", "ESCALATED"},
    "ASSIGNED": {"IN_PROGRESS", "CANCELLED"},
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


@router.post("/{work_order_id}/status")
def update_status(work_order_id: str, payload: StatusUpdateRequest, request: Request) -> dict:
    if payload.idempotency_key in IDEMPOTENCY_RESULTS:
        return IDEMPOTENCY_RESULTS[payload.idempotency_key]
    work_order = WORK_ORDERS.get(work_order_id)
    if work_order is None:
        raise HTTPException(
            status_code=404, detail={"code": "WORK_ORDER_NOT_FOUND", "message": "工单不存在", "retryable": False}
        )
    current = work_order["status"]
    if payload.status not in ALLOWED_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "INVALID_STATE_TRANSITION",
                "message": f"不允许从 {current} 变更到 {payload.status}",
                "retryable": False,
            },
        )
    work_order["status"] = payload.status
    result = {"item": work_order.copy(), "idempotency_key": payload.idempotency_key, "trace_id": request.state.trace_id}
    IDEMPOTENCY_RESULTS[payload.idempotency_key] = result
    return result
