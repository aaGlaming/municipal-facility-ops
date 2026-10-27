from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.core.auth import AuthPrincipal, require_permission
from app.core.dependencies import get_db_session
from app.schemas.facility import (
    PublicReportImportRequest,
    ReportCreate,
    ReportPage,
    ReportStatusUpdate,
)
from app.services.facility_service import (
    create_report,
    find_report,
    list_reports,
    report_dict,
    update_report_status,
)

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("", status_code=201)
def create(
    payload: ReportCreate,
    request: Request,
    response: Response,
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("report:create")),
) -> dict:
    report, created, duplicate_of = create_report(db, principal, request, payload)
    if not created:
        response.status_code = 200
    return {"item": report_dict(report), "created": created, "duplicate_of": duplicate_of}


@router.post("/import/public")
def import_public(
    payload: PublicReportImportRequest,
    request: Request,
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("report:import")),
) -> dict:
    results = []
    created_count = 0
    for row in payload.rows:
        report, created, _ = create_report(db, principal, request, row, public_import=True)
        created_count += int(created)
        results.append(report_dict(report))
    return {"items": results, "created": created_count, "total": len(results)}


@router.get("", response_model=ReportPage)
def list_route(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    region: str | None = Query(default=None, max_length=100),
    status: str | None = Query(default=None, max_length=32),
    category: str | None = Query(default=None, max_length=64),
    source_type: str | None = Query(default=None, max_length=32),
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("report:read")),
) -> dict:
    return list_reports(db, principal, request, page, page_size, region, status, category, source_type)


@router.get("/{report_id}")
def detail(
    report_id: str,
    request: Request,
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("report:read")),
) -> dict:
    return {"item": report_dict(find_report(db, principal, request, report_id))}


@router.patch("/{report_id}/status")
def update_status(
    report_id: str,
    payload: ReportStatusUpdate,
    request: Request,
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("report:update")),
) -> dict:
    return {"item": report_dict(update_report_status(db, principal, request, report_id, payload.status))}
