from datetime import datetime

from app.core.auth import AuthPrincipal
from app.db.base import Base
from app.models.facility import Facility, Location
from app.schemas.agent import ToolCallRequest
from app.tools.runner import execute_tool
from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


def _request() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/agent-tools", "headers": []})


def _principal(*permissions: str) -> AuthPrincipal:
    return AuthPrincipal("agent-user", {"admin"}, set(permissions), {"*"})


def _call(
    tool_name: str, arguments: dict, *, agent_name: str = "triage", confirmation: bool = False
) -> ToolCallRequest:
    return ToolCallRequest(
        tool_call_id=f"CALL-{tool_name.replace('.', '-')}",
        agent_run_id="RUN-1",
        trace_id="TRACE-1",
        agent_name=agent_name,
        tool_name=tool_name,
        arguments=arguments,
        idempotency_key=f"idem-{tool_name}-1-123456",
        human_confirmation=confirmation,
    )


def _session() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add(
        Location(
            id=1,
            address="10 Main Street",
            district="North",
            region="DISTRICT-01",
            latitude=40.7,
            longitude=-74.0,
            source_type="synthetic",
            source_system="test",
        )
    )
    session.add(
        Facility(
            id="FAC-TOOL",
            facility_code="LIGHT-TOOL",
            type="street_light",
            name="Tool Test Light",
            status="active",
            location_id=1,
            region="DISTRICT-01",
            source_type="synthetic",
            source_system="test",
        )
    )
    session.commit()
    return session


def test_invalid_tool_arguments_are_rejected_before_execution() -> None:
    with _session() as db:
        result = execute_tool(
            db,
            _principal("facility:read"),
            _request(),
            _call("facility.search", {"page_size": 1000}),
        )
    assert result.status == "FAILED"
    assert result.error is not None
    assert result.error.code == "INVALID_ARGUMENT"


def test_tool_permission_is_checked_before_business_execution() -> None:
    with _session() as db:
        result = execute_tool(db, _principal(), _request(), _call("facility.search", {"query": "light"}))
    assert result.status == "FAILED"
    assert result.error is not None
    assert result.error.code == "PERMISSION_DENIED"


def test_facility_search_tool_returns_limited_structured_output() -> None:
    with _session() as db:
        result = execute_tool(
            db,
            _principal("facility:read"),
            _request(),
            _call("facility.search", {"query": "Tool Test"}, agent_name="facility"),
        )
    assert result.status == "SUCCEEDED"
    assert result.result["total"] == 1
    assert result.result["items"][0]["id"] == "FAC-TOOL"


def test_high_risk_tool_requires_confirmation() -> None:
    with _session() as db:
        result = execute_tool(
            db,
            _principal("work_order:write"),
            _request(),
            _call(
                "work_order.update_status",
                {"work_order_id": "WO-1", "target_status": "CLOSED"},
                agent_name="dispatch",
            ),
        )
    assert result.status == "PENDING_CONFIRMATION"
    assert result.error is not None
    assert result.error.code == "HUMAN_CONFIRMATION_REQUIRED"


def test_read_tool_executes_and_repeated_idempotency_returns_duplicate() -> None:
    with _session() as db:
        first = execute_tool(
            db,
            _principal("work_order:read"),
            _request(),
            _call(
                "sla.calculate",
                {
                    "issue_type": "street_light",
                    "priority": "P2",
                    "reported_at": datetime(2026, 10, 27, 10, 0, 0),
                },
                agent_name="sla",
            ),
        )
        second = execute_tool(
            db,
            _principal("work_order:read"),
            _request(),
            _call(
                "sla.calculate",
                {
                    "issue_type": "street_light",
                    "priority": "P2",
                    "reported_at": datetime(2026, 10, 27, 10, 0, 0),
                },
                agent_name="sla",
            ),
        )
    assert first.status == "SUCCEEDED"
    assert first.result["item"]["sla_minutes"] == 24 * 60
    assert second.status == "DUPLICATE"
    assert second.duplicate_of == first.tool_call_id
