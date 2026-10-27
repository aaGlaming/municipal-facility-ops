from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

from app.core.auth import AuthPrincipal, require_permission
from app.core.config import Settings
from app.core.dependencies import get_db_session, get_settings_dependency
from app.schemas.rag import DocumentDetailResponse
from app.services.document_service import document_dict, get_document, part_dict, upload_document

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/documents", status_code=201, response_model=DocumentDetailResponse)
async def upload(
    request: Request,
    file: UploadFile = File(...),
    facility_type: str | None = Form(default=None),
    region: str | None = Form(default=None),
    effective_date: date | None = Form(default=None),
    expiry_date: date | None = Form(default=None),
    version: str = Form(default="v1"),
    source_type: Literal["internal", "public"] = Form(default="internal"),
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dependency),
    principal: AuthPrincipal = Depends(require_permission("document:upload")),
) -> dict:
    document, parts = await upload_document(
        db,
        settings,
        principal,
        request,
        file,
        facility_type,
        region,
        effective_date,
        expiry_date,
        version,
        source_type,
    )
    return {"item": document_dict(document), "parts": [part_dict(part) for part in parts]}


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
def detail(
    document_id: str,
    request: Request,
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("document:read")),
) -> dict:
    document, parts = get_document(db, principal, request, document_id)
    return {"item": document_dict(document), "parts": [part_dict(part) for part in parts]}
