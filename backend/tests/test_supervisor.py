from app.agents.supervisor import Supervisor, SupervisorDecision, route_intent
from app.core.auth import AuthPrincipal
from app.core.config import Settings
from app.db.base import Base
from app.models import AgentRun
from app.schemas.agent import AgentRequest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request


def _request() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/agents", "headers": []})


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _agent_request(**kwargs) -> AgentRequest:
    data = {
        "request_id": "REQ-20",
        "trace_id": "TRACE-20",
        "session_id": "SESSION-20",
        "user_id": "USER-20",
        "agent_name": "supervisor",
        "intent": "查询设施台账",
        "input": {},
        "max_model_calls": 3,
        "max_tool_calls": 3,
        "timeout_seconds": 10,
    }
    data.update(kwargs)
    return AgentRequest(**data)


def _principal() -> AuthPrincipal:
    return AuthPrincipal("user-20", {"admin"}, {"*"}, {"*"})


def _llm_settings() -> Settings:
    return Settings(LLM_API_KEY="key", LLM_MODEL="model")


def test_routes_to_seven_specialists() -> None:
    assert route_intent("现场安全风险") == "safety"
    assert route_intent("设施台账") == "facility"
    assert route_intent("未知请求") == "triage"


def test_missing_model_stops_with_evidence_insufficient() -> None:
    db = _db()
    response = Supervisor(model=None).run(db, _principal(), _request(), _agent_request())
    assert response.status == "FAILED"
    assert response.stop_reason == "EVIDENCE_INSUFFICIENT"
    assert db.get(AgentRun, response.agent_run_id) is not None


def test_tool_then_answer_and_persists_counters() -> None:
    db = _db()
    calls = iter(
        [
            SupervisorDecision(action="tool", tool_name="facility.search", arguments={"query": "中心"}),
            SupervisorDecision(action="answer", answer="已完成设施查询"),
        ]
    )
    response = Supervisor(model=lambda state: next(calls), settings=_llm_settings()).run(
        db, _principal(), _request(), _agent_request()
    )
    assert response.status == "SUCCEEDED"
    assert response.stop_reason == "COMPLETED"
    row = db.get(AgentRun, response.agent_run_id)
    assert row is not None and row.iterations == 3


def test_timeout_and_budget_stop() -> None:
    db = _db()
    response = Supervisor(
        model=lambda state: SupervisorDecision(action="tool", tool_name="facility.search", arguments={"query": "x"}),
        settings=_llm_settings(),
    ).run(db, _principal(), _request(), _agent_request(max_model_calls=1))
    assert response.stop_reason == "MAX_MODEL_CALLS"
