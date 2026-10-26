import pytest
from app.api.routes import auth as auth_route
from app.core.auth import TokenError, decode_access_token, issue_access_token
from app.core.config import Settings
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _token(*, permissions: list[str], regions: list[str] | None = None, roles: list[str] | None = None) -> str:
    secret = Settings().auth_secret
    return issue_access_token(
        subject="user-test",
        roles=roles or ["dispatcher"],
        permissions=permissions,
        regions=regions or ["*"],
        secret=secret,
        ttl_seconds=900,
    )


def test_token_round_trip_and_expiry_validation() -> None:
    token = issue_access_token(
        subject="user-1",
        roles=["dispatcher"],
        permissions=["facility:read"],
        regions=["DISTRICT-01"],
        secret="test-secret-please-use-a-long-value",
        ttl_seconds=900,
    )
    claims = decode_access_token(token, "test-secret-please-use-a-long-value")
    assert claims.subject == "user-1"
    assert claims.permissions == {"facility:read"}
    assert claims.regions == {"DISTRICT-01"}
    expired = issue_access_token("user-1", [], [], ["*"], "test-secret-please-use-a-long-value", ttl_seconds=-1)
    with pytest.raises(TokenError):
        decode_access_token(expired, "test-secret-please-use-a-long-value")


def test_facility_route_rejects_missing_permission_and_allows_authorized_token() -> None:
    denied = client.get("/api/facilities")
    assert denied.status_code == 401
    assert denied.json()["code"] == "AUTHENTICATION_REQUIRED"
    allowed = client.get(
        "/api/facilities",
        headers={"Authorization": f"Bearer {_token(permissions=['facility:read'])}"},
    )
    assert allowed.status_code == 200


def test_region_scope_is_enforced_on_facility_list() -> None:
    response = client.get(
        "/api/facilities",
        headers={"Authorization": f"Bearer {_token(permissions=['facility:read'], regions=['DISTRICT-99'])}"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "REGION_SCOPE_DENIED"


def test_high_risk_work_order_transition_requires_confirmation() -> None:
    response = client.post(
        "/api/work-orders/WO-000001/status",
        json={"status": "CLOSED", "idempotency_key": "auth-close-1"},
        headers={"Authorization": f"Bearer {_token(permissions=['work_order:write'])}"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "HUMAN_CONFIRMATION_REQUIRED"


def test_login_records_success_and_issues_token(monkeypatch) -> None:
    settings = Settings(
        AUTH_SECRET="test-secret-please-use-a-long-value",
        AUTH_BOOTSTRAP_USERNAME="dispatcher",
        AUTH_BOOTSTRAP_PASSWORD="test-password",
    )
    monkeypatch.setattr(auth_route, "get_settings", lambda: settings)
    response = client.post("/api/auth/login", json={"username": "dispatcher", "password": "test-password"})
    assert response.status_code == 200
    assert response.json()["token_type"] == "Bearer"
    assert response.json()["access_token"]
