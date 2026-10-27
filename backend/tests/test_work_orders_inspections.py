from app.core.auth import issue_access_token
from app.core.config import Settings
from fastapi.testclient import TestClient


def _headers(*permissions: str, regions: tuple[str, ...] = ("*",)) -> dict[str, str]:
    token = issue_access_token(
        "dispatcher-test", ["dispatcher"], list(permissions), list(regions), Settings().auth_secret, 900
    )
    return {"Authorization": f"Bearer {token}"}


def test_work_order_creation_is_idempotent_and_calculates_sla(client: TestClient) -> None:
    payload = {
        "facility_id": "FAC-1",
        "priority": "P1",
        "problem_type": "street_light",
        "idempotency_key": "wo-step13-1",
    }
    first = client.post("/api/work-orders", json=payload, headers=_headers("work_order:create"))
    assert first.status_code == 201
    assert first.json()["item"]["status"] == "NEW"
    assert first.json()["item"]["due_at"]
    repeated = client.post("/api/work-orders", json=payload, headers=_headers("work_order:create"))
    assert repeated.status_code == 200
    assert repeated.json()["item"]["id"] == first.json()["item"]["id"]


def test_work_order_state_machine_assignment_acceptance_and_rework(client: TestClient) -> None:
    headers = _headers("work_order:create", "work_order:write", "work_order:accept")
    created = client.post(
        "/api/work-orders",
        json={"facility_id": "FAC-1", "priority": "P2", "idempotency_key": "wo-step13-2"},
        headers=headers,
    )
    order_id = created.json()["item"]["id"]
    for status, extra in [
        ("TRIAGED", {}),
        ("ASSIGNED", {"assignee_id": "TECH-1"}),
        ("IN_PROGRESS", {}),
        ("WAITING_CONFIRMATION", {}),
        ("COMPLETED", {"handling_notes": "Replaced lamp", "evidence_uri": "https://example/evidence.jpg"}),
    ]:
        response = client.post(
            f"/api/work-orders/{order_id}/status",
            json={"status": status, "idempotency_key": f"{order_id}-{status}", **extra},
            headers=headers,
        )
        assert response.status_code == 200, response.text
    rejected = client.post(
        f"/api/work-orders/{order_id}/acceptance",
        json={"result": "REJECTED", "reason": "Evidence is insufficient", "evidence_uri": "https://example/reject.jpg"},
        headers=headers,
    )
    assert rejected.status_code == 200
    assert rejected.json()["item"]["status"] == "REJECTED"
    rework = client.post(
        f"/api/work-orders/{order_id}/status",
        json={"status": "IN_PROGRESS", "idempotency_key": f"{order_id}-rework"},
        headers=headers,
    )
    assert rework.status_code == 200
    illegal = client.post(
        f"/api/work-orders/{order_id}/status",
        json={"status": "NEW", "idempotency_key": f"{order_id}-illegal"},
        headers=headers,
    )
    assert illegal.status_code == 409


def test_overdue_work_orders_are_escalated(client: TestClient) -> None:
    headers = _headers("work_order:create", "work_order:write")
    created = client.post(
        "/api/work-orders",
        json={
            "facility_id": "FAC-1",
            "priority": "P1",
            "idempotency_key": "wo-step13-overdue",
            "due_at": "2020-01-01T00:00:00",
        },
        headers=headers,
    )
    assert created.status_code == 201
    escalated = client.post("/api/work-orders/escalate-overdue", headers=headers)
    assert escalated.status_code == 200
    assert escalated.json()["escalated"] >= 1


def test_work_order_rejects_unknown_vendor(client: TestClient) -> None:
    response = client.post(
        "/api/work-orders",
        json={"facility_id": "FAC-1", "vendor_id": "VENDOR-404", "idempotency_key": "wo-step13-vendor"},
        headers=_headers("work_order:create"),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "VENDOR_NOT_FOUND"


def test_inspection_task_can_be_assigned_deferred_and_completed(client: TestClient) -> None:
    headers = _headers("inspection:create", "inspection:write", "inspection:read")
    created = client.post(
        "/api/inspections",
        json={"facility_id": "FAC-1", "priority": "P2", "scheduled_at": "2026-10-27T09:00:00"},
        headers=headers,
    )
    assert created.status_code == 201
    task_id = created.json()["item"]["id"]
    assigned = client.patch(f"/api/inspections/{task_id}/assign", json={"assignee_id": "TECH-1"}, headers=headers)
    assert assigned.status_code == 200
    started = client.patch(f"/api/inspections/{task_id}/status", json={"status": "IN_PROGRESS"}, headers=headers)
    assert started.status_code == 200
    deferred = client.patch(
        f"/api/inspections/{task_id}/status",
        json={"status": "DEFERRED", "reason": "Severe weather"},
        headers=headers,
    )
    assert deferred.status_code == 200
    completed = client.patch(
        f"/api/inspections/{task_id}/status",
        json={"status": "COMPLETED", "result_notes": "No defect found"},
        headers=headers,
    )
    assert completed.status_code == 409
    resumed = client.patch(f"/api/inspections/{task_id}/status", json={"status": "IN_PROGRESS"}, headers=headers)
    assert resumed.status_code == 200
    completed = client.patch(
        f"/api/inspections/{task_id}/status",
        json={"status": "COMPLETED", "result_notes": "No defect found"},
        headers=headers,
    )
    assert completed.status_code == 200
    listed = client.get("/api/inspections?status=COMPLETED", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
