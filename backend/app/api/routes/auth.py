import hmac

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.auth import AuthPrincipal, get_current_principal, issue_access_token, menus_for_principal
from app.core.config import get_settings
from app.schemas.auth import CurrentUserResponse, LoginRequest, TokenResponse
from app.services.audit_service import record_security_event

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request) -> TokenResponse:
    settings = get_settings()
    if not settings.auth_bootstrap_username or not settings.auth_bootstrap_password:
        record_security_event("login_failed", request=request, details={"reason": "auth_not_configured"})
        raise HTTPException(
            status_code=503, detail={"code": "AUTH_NOT_CONFIGURED", "message": "认证服务尚未配置", "retryable": True}
        )
    valid = hmac.compare_digest(payload.username, settings.auth_bootstrap_username) and hmac.compare_digest(
        payload.password, settings.auth_bootstrap_password
    )
    if not valid:
        record_security_event("login_failed", request=request, details={"username": payload.username})
        raise HTTPException(
            status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "用户名或密码错误", "retryable": False}
        )
    roles = [item.strip() for item in settings.auth_bootstrap_roles.split(",") if item.strip()]
    permissions = [item.strip() for item in settings.auth_bootstrap_permissions.split(",") if item.strip()]
    token = issue_access_token(
        payload.username, roles, permissions, ["*"], settings.auth_secret, settings.auth_token_ttl_seconds
    )
    record_security_event("login_succeeded", request=request, subject=payload.username)
    return TokenResponse(access_token=token, expires_in=settings.auth_token_ttl_seconds)


@router.get("/me", response_model=CurrentUserResponse)
def current_user(principal: AuthPrincipal = Depends(get_current_principal)) -> CurrentUserResponse:
    return CurrentUserResponse(
        subject=principal.subject,
        roles=sorted(principal.roles),
        permissions=sorted(principal.permissions),
        regions=sorted(principal.regions),
        menus=menus_for_principal(principal),
    )
