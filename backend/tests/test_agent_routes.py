from app.core.auth import issue_access_token
from app.core.config import Settings
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _headers() -> dict[str, str]:
    token = issue_access_token("agent-user", ["dispatcher"], ["agent:run"], ["*"], Settings().auth_secret, 900)
    return {"Authorization": f"Bearer {token}"}


def test_agent_run_exposes_trace_and_observation() -> None:
    response = client.post(
        "/api/agents/runs",
        json={"intent": "问题分诊", "description": "路灯不亮", "session_id": "SESSION-26", "region": "中心区"},
        headers=_headers(),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["trace_id"]
    assert body["response"]["status"] == "SUCCEEDED"
    trace = client.get(f"/api/agents/runs/{body['agent_run_id']}/trace", headers=_headers())
    assert trace.status_code == 200
    assert trace.json()["trace_id"] == body["trace_id"]
    assert trace.json()["observations"]


def test_high_risk_run_requires_confirmation_and_can_be_rejected() -> None:
    response = client.post(
        "/api/agents/runs",
        json={
            "intent": "安全作业审批",
            "description": "带电封路维修",
            "session_id": "SESSION-26-RISK",
            "region": "中心区",
        },
        headers=_headers(),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["response"]["status"] == "WAITING_CONFIRMATION"
    decision = client.post(
        f"/api/agents/runs/{body['agent_run_id']}/confirmation",
        json={"decision": "reject", "reason": "现场条件未确认"},
        headers=_headers(),
    )
    assert decision.status_code == 200
    assert decision.json()["response"]["status"] == "CANCELLED"


def test_agent_run_can_cancel_and_retry() -> None:
    response = client.post(
        "/api/agents/runs",
        json={"intent": "问题分诊", "description": "路面坑洞", "session_id": "SESSION-26-CANCEL", "region": "中心区"},
        headers=_headers(),
    )
    run_id = response.json()["agent_run_id"]
    cancelled = client.post(f"/api/agents/runs/{run_id}/cancel", json={"reason": "重复报修"}, headers=_headers())
    assert cancelled.status_code == 200
    retry = client.post(f"/api/agents/runs/{run_id}/retry", headers=_headers())
    assert retry.status_code == 201
    assert retry.json()["agent_run_id"] != run_id
