from datetime import datetime

from app.agents.scheduling_agent import SchedulingAgent
from app.agents.triage_agent import classify_issue
from app.core.auth import issue_access_token
from app.core.config import Settings
from app.schemas.scheduling import SlaPlanRequest
from app.schemas.triage import TriageRequest


def _headers(*permissions: str) -> dict[str, str]:
    token = issue_access_token(
        "e2e-operator", ["dispatcher"], list(permissions), ["DISTRICT-01"], Settings().auth_secret, 900
    )
    return {"Authorization": f"Bearer {token}"}


def test_report_to_closed_work_order_and_audit(client) -> None:
    permissions = (
        "report:create",
        "report:read",
        "report:update",
        "facility:read",
        "inspection:create",
        "inspection:write",
        "inspection:read",
        "work_order:create",
        "work_order:read",
        "work_order:write",
        "work_order:accept",
        "agent:run",
        "audit:read",
    )
    headers = _headers(*permissions)
    report_payload = {
        "description": "人民路路灯整晚不亮，影响夜间通行",
        "category": "street_light",
        "facility_id": "FAC-1",
        "region": "DISTRICT-01",
        "idempotency_key": "e2e-report-001",
    }
    created = client.post("/api/reports", json=report_payload, headers=headers)
    assert created.status_code == 201
    report_id = created.json()["item"]["id"]
    repeated = client.post("/api/reports", json=report_payload, headers=headers)
    assert repeated.status_code == 200 and repeated.json()["created"] is False
    assert repeated.json()["item"]["id"] == report_id

    category, _, priority = classify_issue(
        TriageRequest(description=report_payload["description"], region="DISTRICT-01")
    )
    assert category == "street_light" and priority == "P3"
    sla = SchedulingAgent().plan_sla(
        SlaPlanRequest(
            issue_type=category,
            priority=priority,
            region="DISTRICT-01",
            reported_at=datetime(2026, 10, 27, 9, 0),
            public_safety=False,
            repeated_report=False,
        )
    )
    assert sla.sla_minutes == 3 * 24 * 60
    triaged = client.patch(f"/api/reports/{report_id}/status", json={"status": "TRIAGED"}, headers=headers)
    assert triaged.status_code == 200
    linked = client.patch(f"/api/reports/{report_id}/status", json={"status": "LINKED"}, headers=headers)
    assert linked.status_code == 200

    inspection = client.post(
        "/api/inspections",
        json={"facility_id": "FAC-1", "priority": priority, "region": "DISTRICT-01"},
        headers=headers,
    )
    assert inspection.status_code == 201
    inspection_id = inspection.json()["item"]["id"]
    assert (
        client.patch(
            f"/api/inspections/{inspection_id}/assign", json={"assignee_id": "TECH-1"}, headers=headers
        ).status_code
        == 200
    )
    assert (
        client.patch(
            f"/api/inspections/{inspection_id}/status", json={"status": "IN_PROGRESS"}, headers=headers
        ).status_code
        == 200
    )
    inspection_done = client.patch(
        f"/api/inspections/{inspection_id}/status",
        json={"status": "COMPLETED", "result_notes": "现场确认路灯故障"},
        headers=headers,
    )
    assert inspection_done.status_code == 200

    order = client.post(
        "/api/work-orders",
        json={"report_id": report_id, "facility_id": "FAC-1", "priority": priority, "idempotency_key": "e2e-order-001"},
        headers=headers,
    )
    assert order.status_code == 201
    order_id = order.json()["item"]["id"]
    for status, extra in [
        ("TRIAGED", {}),
        ("ASSIGNED", {"assignee_id": "TECH-1"}),
        ("IN_PROGRESS", {}),
        ("WAITING_CONFIRMATION", {}),
        ("COMPLETED", {"handling_notes": "更换路灯并恢复照明", "evidence_uri": "https://evidence.example/e2e-001.jpg"}),
    ]:
        response = client.post(
            f"/api/work-orders/{order_id}/status",
            json={"status": status, "idempotency_key": f"e2e-order-001-{status}", **extra},
            headers=headers,
        )
        assert response.status_code == 200, response.text
    accepted = client.post(
        f"/api/work-orders/{order_id}/acceptance",
        json={
            "result": "ACCEPTED",
            "reason": "照片和现场结果核验通过",
            "evidence_uri": "https://evidence.example/e2e-001.jpg",
        },
        headers=headers,
    )
    assert accepted.status_code == 200 and accepted.json()["item"]["status"] == "ACCEPTED"
    closed = client.post(
        f"/api/work-orders/{order_id}/status",
        json={"status": "CLOSED", "idempotency_key": "e2e-order-001-close", "human_confirmation": True},
        headers=headers,
    )
    assert closed.status_code == 200 and closed.json()["item"]["status"] == "CLOSED"

    pending = client.post(
        "/api/agents/runs",
        json={"intent": "封路派工", "description": "需要封路并安排维修", "session_id": "e2e-session"},
        headers=headers,
    )
    assert pending.status_code == 201 and pending.json()["status"] == "WAITING_CONFIRMATION"
    run_id = pending.json()["agent_run_id"]
    approved = client.post(
        f"/api/agents/runs/{run_id}/confirmation",
        json={"decision": "approve", "reason": "授权人员已确认"},
        headers=headers,
    )
    assert approved.status_code == 200 and approved.json()["status"] == "SUCCEEDED"

    audit = client.get("/api/monitoring/audit?limit=200", headers=headers)
    assert audit.status_code == 200
    event_types = {item["event_type"] for item in audit.json()["items"]}
    assert {"citizen_report_created", "work_order_accepted", "work_order_status_changed"} <= event_types


def test_e2e_region_and_permission_boundaries(client) -> None:
    limited = _headers("report:create", "report:read")
    denied = client.post(
        "/api/reports",
        json={"description": "越权区域测试", "region": "DISTRICT-99", "idempotency_key": "e2e-denied-001"},
        headers=limited,
    )
    assert denied.status_code == 403 and denied.json()["code"] == "REGION_SCOPE_DENIED"
    no_permission = client.get("/api/monitoring/audit", headers=limited)
    assert no_permission.status_code == 403
