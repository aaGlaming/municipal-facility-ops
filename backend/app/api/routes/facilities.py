from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.auth import AuthPrincipal, require_permission
from app.core.dependencies import get_db_session
from app.schemas.facility import FacilityPage
from app.services.facility_service import get_facility, list_facilities, list_facility_events, nearby_facilities

router = APIRouter(prefix="/api/facilities", tags=["facilities"])


@router.get("/nearby")
def nearby(
    request: Request,
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    radius_meters: int = Query(default=1000, ge=1, le=50000),
    facility_type: str | None = Query(default=None, alias="type", max_length=64),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("facility:read")),
) -> dict:
    return nearby_facilities(db, principal, request, latitude, longitude, radius_meters, facility_type, page, page_size)


@router.get("", response_model=FacilityPage)
def list_route(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    facility_type: str | None = Query(default=None, alias="type", max_length=64),
    status: str | None = Query(default=None, max_length=32),
    region: str | None = Query(default=None, max_length=100),
    source_type: str | None = Query(default=None, max_length=32),
    query: str | None = Query(default=None, max_length=255),
    address: str | None = Query(default=None, max_length=255),
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("facility:read")),
) -> dict:
    return list_facilities(
        db, principal, request, page, page_size, facility_type, status, region, source_type, query, address
    )


@router.get("/{facility_id}")
def detail(
    facility_id: str,
    request: Request,
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("facility:read")),
) -> dict:
    return {"item": get_facility(db, principal, request, facility_id)}


@router.get("/{facility_id}/events")
def events(
    facility_id: str,
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("facility:read")),
) -> dict:
    return list_facility_events(db, principal, request, facility_id, page, page_size)
