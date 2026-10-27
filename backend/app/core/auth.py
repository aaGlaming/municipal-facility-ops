"""Authentication, authorization and scope enforcement primitives."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from typing import Any

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.services.audit_service import record_security_event

ISSUER = "municipal-facility-ops"
_bearer = HTTPBearer(auto_error=False)


class TokenError(ValueError):
    """Raised when an access token is malformed, invalid or expired."""


@dataclass(frozen=True)
class AuthPrincipal:
    subject: str
    roles: set[str] = field(default_factory=set)
    permissions: set[str] = field(default_factory=set)
    regions: set[str] = field(default_factory=set)

    def has_permission(self, permission: str) -> bool:
        return "*" in self.permissions or permission in self.permissions or "admin:*" in self.permissions

    def require_permission(self, permission: str) -> None:
        if not self.has_permission(permission):
            raise TokenError(f"missing permission: {permission}")

    def can_access_region(self, region: str | None) -> bool:
        return region is None or "*" in self.regions or region in self.regions or "admin" in self.roles


def _encode(value: dict[str, Any]) -> str:
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _decode(value: str) -> dict[str, Any]:
    try:
        padded = value + "=" * (-len(value) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode())
        result = json.loads(decoded)
    except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise TokenError("invalid token encoding") from exc
    if not isinstance(result, dict):
        raise TokenError("invalid token claims")
    return result


def issue_access_token(
    subject: str,
    roles: list[str],
    permissions: list[str],
    regions: list[str],
    secret: str,
    ttl_seconds: int,
) -> str:
    if not secret or len(secret) < 16:
        raise TokenError("authentication secret is too short")
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": ISSUER,
        "sub": subject,
        "roles": sorted(set(roles)),
        "permissions": sorted(set(permissions)),
        "regions": sorted(set(regions)),
        "iat": now,
        "exp": now + ttl_seconds,
    }
    encoded_header = _encode(header)
    encoded_payload = _encode(payload)
    signing_input = f"{encoded_header}.{encoded_payload}".encode()
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def decode_access_token(token: str, secret: str) -> AuthPrincipal:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
    except ValueError as exc:
        raise TokenError("invalid token structure") from exc
    expected = hmac.new(secret.encode(), f"{encoded_header}.{encoded_payload}".encode(), hashlib.sha256).digest()
    provided = _decode_bytes(encoded_signature)
    if not hmac.compare_digest(expected, provided):
        raise TokenError("invalid token signature")
    header = _decode(encoded_header)
    claims = _decode(encoded_payload)
    if header.get("alg") != "HS256" or header.get("typ") != "JWT" or claims.get("iss") != ISSUER:
        raise TokenError("invalid token claims")
    subject = claims.get("sub")
    expiry = claims.get("exp")
    if not isinstance(subject, str) or not subject or not isinstance(expiry, (int, float)) or time.time() >= expiry:
        raise TokenError("token expired or missing subject")
    values = {key: claims.get(key) for key in ("roles", "permissions", "regions")}
    if not all(isinstance(value, list) and all(isinstance(item, str) for item in value) for value in values.values()):
        raise TokenError("invalid token scopes")
    return AuthPrincipal(subject, set(values["roles"]), set(values["permissions"]), set(values["regions"]))


def _decode_bytes(value: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, TypeError) as exc:
        raise TokenError("invalid token signature") from exc


def _auth_error(code: str, message: str, status_code: int) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message, "retryable": False})


def get_current_principal(
    request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)
) -> AuthPrincipal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        record_security_event("authentication_required", request=request)
        raise _auth_error("AUTHENTICATION_REQUIRED", "需要登录", 401)
    try:
        principal = decode_access_token(credentials.credentials, get_settings().auth_secret)
    except TokenError:
        record_security_event("invalid_token", request=request)
        raise _auth_error("INVALID_TOKEN", "令牌无效或已过期", 401) from None
    return principal


def require_permission(permission: str):
    def dependency(request: Request, principal: AuthPrincipal = Depends(get_current_principal)) -> AuthPrincipal:
        if not principal.has_permission(permission):
            record_security_event(
                "permission_denied", request=request, subject=principal.subject, details={"permission": permission}
            )
            raise _auth_error("PERMISSION_DENIED", "没有执行该操作的权限", 403)
        return principal

    return dependency


def ensure_region_access(principal: AuthPrincipal, region: str | None, request: Request | None = None) -> None:
    if not principal.can_access_region(region):
        if request is not None:
            record_security_event(
                "region_scope_denied", request=request, subject=principal.subject, details={"region": region}
            )
        raise _auth_error("REGION_SCOPE_DENIED", "超出用户区域范围", 403)


def require_human_confirmation(
    principal: AuthPrincipal, action: str, confirmed: bool, request: Request | None = None
) -> None:
    if not confirmed:
        if request is not None:
            record_security_event(
                "human_confirmation_required", request=request, subject=principal.subject, details={"action": action}
            )
        raise _auth_error("HUMAN_CONFIRMATION_REQUIRED", "该高风险操作需要人工确认", 403)


MENU_PERMISSIONS = {
    "facilities": "facility:read",
    "reports": "report:read",
    "report_creation": "report:create",
    "report_triage": "report:update",
    "public_report_import": "report:import",
    "work_orders": "work_order:read",
    "work_order_updates": "work_order:write",
    "audit": "audit:read",
    "agents": "agent:run",
    "users": "user:manage",
}


def menus_for_principal(principal: AuthPrincipal) -> list[str]:
    return [menu for menu, permission in MENU_PERMISSIONS.items() if principal.has_permission(permission)]
