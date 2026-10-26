from fastapi import HTTPException, Request

from app.core.auth import AuthPrincipal, ensure_region_access, require_human_confirmation


def authorize_work_order_tool(
    principal: AuthPrincipal,
    action: str,
    work_order: dict,
    human_confirmation: bool,
    request: Request,
) -> None:
    if not principal.has_permission("work_order:write"):
        raise HTTPException(
            status_code=403, detail={"code": "PERMISSION_DENIED", "message": "没有执行该操作的权限", "retryable": False}
        )
    ensure_region_access(principal, work_order.get("region"), request)
    if action == "close":
        require_human_confirmation(principal, "close_work_order", human_confirmation, request)
