"""Database-backed facility and citizen-report operations."""

from __future__ import annotations

import math
import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException, Request
from sqlalchemy import false, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import AuthPrincipal, ensure_region_access
from app.models.facility import CitizenReport, Facility, Location
from app.schemas.facility import ReportCreate
from app.services.audit_service import record_security_event

EARTH_RADIUS_METERS = 6_371_000


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message, "retryable": False})


def _in_scope(principal: AuthPrincipal, column):
    if "*" in principal.regions or "admin" in principal.roles:
        return None
    if not principal.regions:
        return false()
    return column.in_(sorted(principal.regions))


def facility_dict(facility: Facility, location: Location | None = None, distance: float | None = None) -> dict:
    location_data = None
    if location is not None:
        location_data = {
            "address": location.address,
            "district": location.district,
            "region": location.region,
            "latitude": float(location.latitude) if location.latitude is not None else None,
            "longitude": float(location.longitude) if location.longitude is not None else None,
        }
    return {
        "id": facility.id,
        "facility_code": facility.facility_code,
        "type": facility.type,
        "name": facility.name,
        "status": facility.status,
        "criticality": facility.criticality,
        "region": facility.region,
        "install_date": facility.install_date,
        "condition_score": facility.condition_score,
        "source_type": facility.source_type,
        "source_system": facility.source_system,
        "location": location_data,
        "distance_meters": round(distance, 1) if distance is not None else None,
    }


def list_facilities(
    db: Session,
    principal: AuthPrincipal,
    request: Request,
    page: int,
    page_size: int,
    facility_type: str | None,
    status: str | None,
    region: str | None,
    source_type: str | None,
    query: str | None,
    address: str | None = None,
) -> dict:
    ensure_region_access(principal, region, request)
    stmt = (
        select(Facility, Location)
        .outerjoin(Location, Facility.location_id == Location.id)
        .where(Facility.is_deleted.is_(False))
    )
    scope = _in_scope(principal, Facility.region)
    if scope is not None:
        stmt = stmt.where(scope)
    if facility_type:
        stmt = stmt.where(Facility.type == facility_type)
    if status:
        stmt = stmt.where(Facility.status == status)
    if region:
        stmt = stmt.where(Facility.region == region)
    if source_type:
        stmt = stmt.where(Facility.source_type == source_type)
    if query or address:
        pattern = f"%{(query or address or '').strip()}%"
        stmt = stmt.where(
            or_(Facility.name.ilike(pattern), Facility.facility_code.ilike(pattern), Location.address.ilike(pattern))
        )
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = db.scalar(count_stmt) or 0
    rows = db.execute(stmt.order_by(Facility.id).offset((page - 1) * page_size).limit(page_size)).all()
    if (
        total == 0
        and region is None
        and principal.regions
        and "*" not in principal.regions
        and "admin" not in principal.roles
    ):
        # Preserve Step 11's explicit signal when a scoped user asks for a global list but has no visible records.
        ensure_region_access(principal, "__no_matching_region__", request)
    return {
        "items": [facility_dict(facility, location) for facility, location in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_facility(db: Session, principal: AuthPrincipal, request: Request, facility_id: str) -> dict:
    row = db.execute(
        select(Facility, Location)
        .outerjoin(Location, Facility.location_id == Location.id)
        .where(Facility.id == facility_id, Facility.is_deleted.is_(False))
    ).first()
    if row is None:
        raise _error(404, "FACILITY_NOT_FOUND", "设施不存在")
    facility, location = row
    ensure_region_access(principal, facility.region, request)
    return facility_dict(facility, location)


def _distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    value = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_METERS * math.asin(min(1.0, math.sqrt(value)))


def nearby_facilities(
    db: Session,
    principal: AuthPrincipal,
    request: Request,
    latitude: float,
    longitude: float,
    radius_meters: int,
    facility_type: str | None,
    page: int,
    page_size: int,
) -> dict:
    stmt = (
        select(Facility, Location)
        .join(Location, Facility.location_id == Location.id)
        .where(Facility.is_deleted.is_(False), Location.latitude.is_not(None), Location.longitude.is_not(None))
    )
    scope = _in_scope(principal, Facility.region)
    if scope is not None:
        stmt = stmt.where(scope)
    if facility_type:
        stmt = stmt.where(Facility.type == facility_type)
    matches: list[tuple[Facility, Location, float]] = []
    for facility, location in db.execute(stmt).all():
        ensure_region_access(principal, facility.region, request)
        distance = _distance_meters(latitude, longitude, float(location.latitude), float(location.longitude))
        if distance <= radius_meters:
            matches.append((facility, location, distance))
    matches.sort(key=lambda item: (item[2], item[0].id))
    total = len(matches)
    start = (page - 1) * page_size
    selected = matches[start : start + page_size]
    return {
        "items": [facility_dict(facility, location, distance) for facility, location, distance in selected],
        "total": total,
        "page": page,
        "page_size": page_size,
        "radius_meters": radius_meters,
    }


def list_facility_events(
    db: Session, principal: AuthPrincipal, request: Request, facility_id: str, page: int, page_size: int
) -> dict:
    facility = db.get(Facility, facility_id)
    if facility is None or facility.is_deleted:
        raise _error(404, "FACILITY_NOT_FOUND", "设施不存在")
    ensure_region_access(principal, facility.region, request)
    base = select(CitizenReport).where(
        CitizenReport.facility_id == facility_id,
        CitizenReport.is_deleted.is_(False),
    )
    scope = _in_scope(principal, CitizenReport.region)
    if scope is not None:
        base = base.where(scope)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    reports = db.scalars(
        base.order_by(CitizenReport.reported_at.desc(), CitizenReport.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {"items": [report_dict(report) for report in reports], "total": total, "page": page, "page_size": page_size}


def report_dict(report: CitizenReport) -> dict:
    return {
        "id": report.id,
        "facility_id": report.facility_id,
        "source": report.source,
        "description": report.description,
        "category": report.category,
        "subcategory": report.subcategory,
        "status": report.status,
        "priority": report.priority,
        "external_id": report.external_id,
        "source_type": report.source_type,
        "source_system": report.source_system,
        "data_version": report.data_version,
        "region": report.region,
        "latitude": float(report.latitude) if report.latitude is not None else None,
        "longitude": float(report.longitude) if report.longitude is not None else None,
        "reported_at": report.reported_at,
    }


def _normalized_description(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def _candidate_duplicate(db: Session, payload: ReportCreate, region: str) -> CitizenReport | None:
    if not payload.category:
        return None
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=24)
    candidates = db.scalars(
        select(CitizenReport)
        .where(
            CitizenReport.category == payload.category,
            CitizenReport.region == region,
            CitizenReport.reported_at >= cutoff,
            CitizenReport.is_deleted.is_(False),
        )
        .order_by(CitizenReport.reported_at.desc())
        .limit(100)
    ).all()
    description = _normalized_description(payload.description)
    for candidate in candidates:
        if _normalized_description(candidate.description) != description:
            continue
        same_facility = payload.facility_id is not None and candidate.facility_id == payload.facility_id
        same_coordinates = (
            payload.latitude is not None
            and payload.longitude is not None
            and candidate.latitude is not None
            and candidate.longitude is not None
            and _distance_meters(
                payload.latitude, payload.longitude, float(candidate.latitude), float(candidate.longitude)
            )
            <= 100
        )
        if same_facility or same_coordinates:
            return candidate
    return None


def create_report(
    db: Session,
    principal: AuthPrincipal,
    request: Request,
    payload: ReportCreate,
    public_import: bool = False,
) -> tuple[CitizenReport, bool, str | None]:
    if payload.facility_id:
        facility = db.get(Facility, payload.facility_id)
        if facility is None or facility.is_deleted:
            raise _error(404, "FACILITY_NOT_FOUND", "关联设施不存在")
        report_region = payload.region or facility.region
        ensure_region_access(principal, facility.region, request)
        if report_region != facility.region:
            raise _error(422, "REGION_MISMATCH", "问题区域必须与关联设施一致")
    else:
        report_region = payload.region
        if report_region is None and len(principal.regions) == 1 and "*" not in principal.regions:
            report_region = next(iter(principal.regions))
    if not report_region:
        raise _error(422, "REGION_REQUIRED", "未关联设施的问题必须提供区域")
    ensure_region_access(principal, report_region, request)
    if payload.idempotency_key:
        existing = db.scalar(select(CitizenReport).where(CitizenReport.idempotency_key == payload.idempotency_key))
        if existing is not None:
            ensure_region_access(principal, existing.region, request)
            return existing, False, None
    source_system = payload.source if public_import else "municipal-facility-ops"
    if payload.external_id:
        existing = db.scalar(
            select(CitizenReport).where(
                CitizenReport.source_system == source_system,
                CitizenReport.external_id == payload.external_id,
            )
        )
        if existing is not None:
            if public_import:
                ensure_region_access(principal, existing.region, request)
                return existing, False, None
            raise _error(409, "DUPLICATE_EXTERNAL_ID", "来源系统编号已导入")
    duplicate = _candidate_duplicate(db, payload, report_region) if not public_import else None
    report = CitizenReport(
        id=f"RPT-{uuid4().hex[:16].upper()}",
        facility_id=payload.facility_id,
        source=payload.source,
        description=payload.description,
        category=payload.category,
        subcategory=payload.subcategory,
        status="NEW",
        external_id=payload.external_id,
        source_type="public" if public_import else "internal",
        source_system=source_system,
        data_version="step12-v1",
        region=report_region,
        latitude=payload.latitude,
        longitude=payload.longitude,
        idempotency_key=payload.idempotency_key,
        reported_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(report)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if payload.external_id:
            if public_import:
                existing = db.scalar(
                    select(CitizenReport).where(
                        CitizenReport.source_system == source_system,
                        CitizenReport.external_id == payload.external_id,
                    )
                )
                if existing is not None:
                    ensure_region_access(principal, existing.region, request)
                    return existing, False, None
            raise _error(409, "DUPLICATE_EXTERNAL_ID", "来源系统编号已导入") from None
        if payload.idempotency_key:
            existing = db.scalar(select(CitizenReport).where(CitizenReport.idempotency_key == payload.idempotency_key))
            if existing is not None:
                ensure_region_access(principal, existing.region, request)
                return existing, False, None
        raise
    db.refresh(report)
    record_security_event(
        "public_report_imported" if public_import else "citizen_report_created",
        request=request,
        subject=principal.subject,
        details={
            "report_id": report.id,
            "source_type": report.source_type,
            "duplicate_of": duplicate.id if duplicate else None,
        },
    )
    return report, True, duplicate.id if duplicate else None


def list_reports(
    db: Session,
    principal: AuthPrincipal,
    request: Request,
    page: int,
    page_size: int,
    region: str | None,
    status: str | None,
    category: str | None,
    source_type: str | None,
) -> dict:
    ensure_region_access(principal, region, request)
    stmt = select(CitizenReport).where(CitizenReport.is_deleted.is_(False))
    scope = _in_scope(principal, CitizenReport.region)
    if scope is not None:
        stmt = stmt.where(scope)
    if region:
        stmt = stmt.where(CitizenReport.region == region)
    if status:
        stmt = stmt.where(CitizenReport.status == status)
    if category:
        stmt = stmt.where(CitizenReport.category == category)
    if source_type:
        stmt = stmt.where(CitizenReport.source_type == source_type)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.scalars(
        stmt.order_by(CitizenReport.reported_at.desc(), CitizenReport.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {"items": [report_dict(report) for report in rows], "total": total, "page": page, "page_size": page_size}


def update_report_status(
    db: Session, principal: AuthPrincipal, request: Request, report_id: str, new_status: str
) -> CitizenReport:
    report = db.get(CitizenReport, report_id)
    if report is None or report.is_deleted:
        raise _error(404, "REPORT_NOT_FOUND", "问题上报不存在")
    ensure_region_access(principal, report.region, request)
    transitions = {
        "NEW": {"TRIAGED", "DUPLICATE", "REJECTED"},
        "TRIAGED": {"LINKED", "DUPLICATE", "REJECTED", "CLOSED"},
        "LINKED": {"TRIAGED", "CLOSED"},
    }
    if new_status not in transitions.get(report.status, set()):
        raise _error(409, "INVALID_REPORT_TRANSITION", f"不允许从 {report.status} 变更到 {new_status}")
    old_status = report.status
    report.status = new_status
    report.version += 1
    report.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(report)
    record_security_event(
        "citizen_report_status_changed",
        request=request,
        subject=principal.subject,
        details={"report_id": report.id, "from": old_status, "to": new_status},
    )
    return report


def find_report(db: Session, principal: AuthPrincipal, request: Request, report_id: str) -> CitizenReport:
    report = db.get(CitizenReport, report_id)
    if report is None or report.is_deleted:
        raise _error(404, "REPORT_NOT_FOUND", "问题上报不存在")
    ensure_region_access(principal, report.region, request)
    return report
