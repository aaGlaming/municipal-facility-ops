from app.core.auth import issue_access_token
from app.core.config import Settings


def _headers(*permissions: str) -> dict[str, str]:
    token = issue_access_token("monitor-user", ["admin"], list(permissions), ["*"], Settings().auth_secret, 900)
    return {"Authorization": f"Bearer {token}"}


def test_monitoring_overview_and_runs_are_permissioned(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.routes.monitoring.check_dependencies",
        lambda settings: {"mysql": "ok", "chroma": "not_configured", "llm": "not_configured"},
    )
    headers = _headers("agent:read")
    overview = client.get("/api/monitoring/overview", headers=headers)
    assert overview.status_code == 200
    assert {"requests", "error_rate", "latency_ms", "dependencies", "alerts"} <= overview.json()["metrics"].keys()
    runs = client.get("/api/monitoring/runs", headers=headers)
    assert runs.status_code == 200
    assert runs.json()["items"] == []


def test_audit_endpoint_is_permissioned_and_reads_append_only_stream(client, tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "security_events.jsonl").write_text(
        '{"event_type":"permission_denied","subject":"user-1","details":{"token":"[REDACTED]"}}\n',
        encoding="utf-8",
    )
    response = client.get("/api/monitoring/audit", headers=_headers("audit:read"))
    assert response.status_code == 200
    assert response.json()["items"][0]["event_type"] == "permission_denied"
    assert client.get("/api/monitoring/audit", headers=_headers("agent:read")).status_code == 403
