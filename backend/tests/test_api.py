from fastapi.testclient import TestClient

from app.main import app


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
