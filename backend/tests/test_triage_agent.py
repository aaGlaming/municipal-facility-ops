from datetime import datetime

from app.agents.triage_agent import TriageAgent
from app.core.auth import AuthPrincipal
from app.db.base import Base
from app.models import CitizenReport, Facility, Location
from app.schemas.triage import TriageRequest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request


def _http() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/triage", "headers": []})


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    location = Location(id=1, address="中心区人民路 1 号", region="中心区", source_type="test", source_system="test")
    facility = Facility(
        id="FAC-TRIAGE",
        facility_code="LIGHT-001",
        type="street_light",
        name="中心区路灯",
        region="中心区",
        location_id=1,
        source_type="test",
        source_system="test",
    )
    db.add_all([location, facility])
    db.commit()
    return db


def _principal() -> AuthPrincipal:
    return AuthPrincipal("triage-user", {"admin"}, {"facility:read"}, {"中心区"})


def test_high_confidence_facility_match_is_selected() -> None:
    result = TriageAgent().run(
        _db(),
        _principal(),
        _http(),
        TriageRequest(description="中心区人民路 1 号路灯不亮", address="中心区人民路 1 号", region="中心区"),
    )
    assert result.category == "street_light"
    assert result.priority == "P3"
    assert result.selected_facility_id == "FAC-TRIAGE"
    assert result.requires_confirmation is False


def test_low_confidence_does_not_bind_facility() -> None:
    result = TriageAgent().run(
        _db(),
        _principal(),
        _http(),
        TriageRequest(description="这里有问题", region="中心区"),
    )
    assert result.requires_confirmation is True
    assert result.selected_facility_id is None
    assert "facility_identifier" in result.missing_fields


def test_duplicate_reports_are_returned() -> None:
    db = _db()
    db.add(
        CitizenReport(
            id="RPT-DUP",
            source="web",
            description="中心区人民路 1 号路灯不亮",
            category="street_light",
            status="NEW",
            source_type="internal",
            source_system="test",
            data_version="v1",
            region="中心区",
            reported_at=datetime.now(),
        )
    )
    db.commit()
    result = TriageAgent().run(
        db, _principal(), _http(), TriageRequest(description="中心区人民路 1 号路灯不亮", region="中心区")
    )
    assert result.duplicate_reports[0].report_id == "RPT-DUP"
