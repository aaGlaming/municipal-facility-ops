"""Service-layer guards for work-order state changes."""

from fastapi import HTTPException, Request

from app.core.auth import AuthPrincipal, ensure_region_access, require_human_confirmation


def authorize_work_order_update(
    principal: AuthPrincipal,
    work_order: dict,
    requested_status: str,
    human_confirmation: bool,
    request: Request,
) -> None:
    """Repeat authorization at the service boundary so callers cannot bypass route guards."""
    if not principal.has_permission("work_order:write"):
        raise HTTPException(
            status_code=403,
            detail={"code": "PERMISSION_DENIED", "message": "没有执行该操作的权限", "retryable": False},
        )
    ensure_region_access(principal, work_order.get("region"), request)
    if requested_status == "CLOSED":
        require_human_confirmation(principal, "close_work_order", human_confirmation, request)
