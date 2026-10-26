import pytest
from app.api.routes import health as health_route
from app.core.config import Settings
from app.main import app
from fastapi.testclient import TestClient
from pydantic import ValidationError

client = TestClient(app)


def test_health_reports_liveness_and_trace_id() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["trace_id"]


def test_invalid_work_order_transition_returns_structured_error() -> None:
    response = client.post(
        "/api/work-orders/WO-000001/status",
        json={"status": "CLOSED", "idempotency_key": "test-transition-1"},
    )
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "INVALID_STATE_TRANSITION"
    assert set(("code", "message", "trace_id", "retryable")) <= body.keys()


def test_facility_list_exposes_source_type() -> None:
    response = client.get("/api/facilities", params={"source_type": "synthetic"})
    assert response.status_code == 200
    body = response.json()
    assert body["items"]
    assert all(item["source_type"] == "synthetic" for item in body["items"])


def test_repeated_status_update_with_same_idempotency_key_is_stable() -> None:
    payload = {"status": "TRIAGED", "idempotency_key": "test-idempotent-1"}
    first = client.post("/api/work-orders/WO-000001/status", json=payload)
    second = client.post("/api/work-orders/WO-000001/status", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()


def test_request_and_trace_ids_are_returned_in_headers() -> None:
    response = client.get("/health", headers={"X-Request-Id": "req-test-1", "X-Trace-Id": "trace-test-1"})
    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == "req-test-1"
    assert response.headers["X-Trace-Id"] == "trace-test-1"
    assert response.json()["trace_id"] == "trace-test-1"


def test_validation_errors_use_standard_error_shape() -> None:
    response = client.post("/api/work-orders/WO-000001/status", json={})
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["retryable"] is False
    assert response.json()["trace_id"]


def test_ready_returns_service_status_and_503_when_dependency_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        health_route,
        "check_dependencies",
        lambda settings: {"mysql": "ok", "chroma": "ok", "llm": "unavailable"},
    )
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"]["llm"] == "unavailable"
    assert response.json()["code"] == "DEPENDENCY_NOT_READY"


def test_invalid_mysql_configuration_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(MYSQL_URL="not-a-mysql-url")
