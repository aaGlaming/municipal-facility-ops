from datetime import datetime, timedelta

from app.agents.scheduling_agent import SchedulingAgent
from app.core.auth import AuthPrincipal
from app.db.base import Base
from app.models import InspectionTask, Technician, WorkOrder
from app.schemas.scheduling import DispatchPlanRequest, InspectionPlanRequest, SlaPlanRequest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request


def _request() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/scheduling", "headers": []})


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    db.add_all(
        [
            Technician(id="TECH-A", name="技术员 A", region="中心区", active=True),
            Technician(id="TECH-B", name="技术员 B", region="中心区", active=True),
        ]
    )
    db.commit()
    return db


def _principal() -> AuthPrincipal:
    return AuthPrincipal("scheduler", {"admin"}, {"*"}, {"中心区"})


def test_sla_plan_escalates_public_safety() -> None:
    result = SchedulingAgent().plan_sla(
        SlaPlanRequest(
            issue_type="traffic_signal",
            priority="P3",
            region="中心区",
            reported_at=datetime(2026, 1, 1),
            public_safety=True,
        )
    )
    assert result.priority == "P1"
    assert result.sla_minutes == 240
    assert result.resolution_due_at > result.first_response_due_at


def test_inspection_plan_returns_candidates_and_confirmation_for_p1() -> None:
    result = SchedulingAgent().plan_inspection(
        _db(),
        _principal(),
        _request(),
        InspectionPlanRequest(region="中心区", priority="P1", requested_at=datetime(2026, 1, 1)),
    )
    assert result.candidate_assignee_ids == ["TECH-A", "TECH-B"]
    assert result.requires_confirmation is True


def test_dispatch_blocks_capacity_and_time_conflict() -> None:
    db = _db()
    start = datetime(2026, 1, 1, 10)
    db.add(
        WorkOrder(
            id="WO-A",
            priority="P2",
            status="ASSIGNED",
            assignee_id="TECH-A",
            region="中心区",
            idempotency_key="wo-a",
            source_type="test",
            source_system="test",
            data_version="v1",
        )
    )
    db.add(
        InspectionTask(
            id="INS-A",
            priority="P2",
            status="ASSIGNED",
            assignee_id="TECH-B",
            region="中心区",
            scheduled_at=start,
            due_at=start + timedelta(hours=2),
            source_type="test",
            source_system="test",
            data_version="v1",
        )
    )
    db.commit()
    result = SchedulingAgent().plan_dispatch(
        db,
        _principal(),
        _request(),
        DispatchPlanRequest(
            region="中心区",
            priority="P2",
            issue_type="street_light",
            scheduled_for=start,
            duration_minutes=60,
            capacity_limit=1,
        ),
    )
    assert result.candidates[0].available is False
    assert result.candidates[1].available is False
    assert result.selected_assignee_id is None
    assert result.blocked_reasons


def test_dispatch_requires_confirmation_for_repeated_or_p1() -> None:
    result = SchedulingAgent().plan_dispatch(
        _db(),
        _principal(),
        _request(),
        DispatchPlanRequest(
            region="中心区",
            priority="P1",
            issue_type="road_damage",
            scheduled_for=datetime(2026, 1, 1),
            repeated_assignment=True,
        ),
    )
    assert result.requires_confirmation is True
    assert "P1 工单派工需要人工确认" in result.confirmation_reasons
    assert "重复派工需要人工确认" in result.confirmation_reasons
