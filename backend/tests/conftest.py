from collections.abc import Generator

import pytest
from app.core.dependencies import get_db_session
from app.db.base import Base
from app.main import app
from app.models.facility import Facility, Location
from app.models.people import Technician, Vendor
from app.models.work_order import WorkOrder
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture(autouse=True)
def test_database() -> Generator[None, None, None]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        session.add(
            Location(
                id=1,
                address="10 Main Street",
                district="North",
                region="DISTRICT-01",
                latitude=40.7000,
                longitude=-74.0000,
                source_type="synthetic",
                source_system="test",
            )
        )
        session.add_all(
            [
                Facility(
                    id="FAC-1",
                    facility_code="LIGHT-1",
                    type="street_light",
                    name="Main Street Light",
                    status="active",
                    location_id=1,
                    region="DISTRICT-01",
                    source_type="synthetic",
                    source_system="test",
                ),
                Facility(
                    id="FAC-2",
                    facility_code="SIGN-1",
                    type="traffic_signal",
                    name="Second Street Signal",
                    status="active",
                    region="DISTRICT-02",
                    source_type="synthetic",
                    source_system="test",
                ),
            ]
        )
        session.add(
            WorkOrder(
                id="WO-000001",
                facility_id="FAC-1",
                priority="P2",
                status="NEW",
                idempotency_key="seed-wo-000001",
                region="DISTRICT-01",
                source_type="synthetic",
                source_system="test",
                data_version="v1",
            )
        )
        session.add(Technician(id="TECH-1", name="Test Technician", region="DISTRICT-01", active=True))
        session.add(Vendor(id="VENDOR-1", name="Test Vendor", region="DISTRICT-01", active=True))
        session.commit()

    def override_db() -> Generator[Session, None, None]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db
    yield
    app.dependency_overrides.pop(get_db_session, None)
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
