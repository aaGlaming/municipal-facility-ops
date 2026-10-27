from collections.abc import Generator

import pytest
from app.core.dependencies import get_db_session
from app.db.base import Base
from app.main import app
from app.models.facility import Facility, Location
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
