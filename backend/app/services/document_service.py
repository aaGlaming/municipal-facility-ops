"""Document upload, safe storage and parse lifecycle service."""

from __future__ import annotations

import hashlib
import os
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import AuthPrincipal, ensure_region_access
from app.core.config import Settings
from app.models.document import Document, DocumentPart
from app.rag.document_parser import (
    DocumentParseError,
    parse_document,
    validate_filename,
    validate_media_type,
)
from app.services.audit_service import record_security_event


def _error(status_code: int, code: str, message: str, **extra: object) -> HTTPException:
    detail: dict[str, object] = {"code": code, "message": message, "retryable": False}
    detail.update(extra)
    return HTTPException(status_code=status_code, detail=detail)


def document_dict(document: Document) -> dict:
    return {
        "id": document.id,
        "original_filename": document.original_filename,
        "storage_key": document.storage_key,
        "media_type": document.media_type,
        "extension": document.extension,
        "size_bytes": document.size_bytes,
        "sha256": document.sha256,
        "status": document.status,
        "error_reason": document.error_reason,
        "uploaded_by": document.uploaded_by,
        "facility_type": document.facility_type,
        "region": document.region,
        "effective_date": document.effective_date,
        "expiry_date": document.expiry_date,
        "version": document.version,
        "source_type": document.source_type,
        "source_system": document.source_system,
        "created_at": document.created_at,
    }


def part_dict(part: DocumentPart) -> dict:
    return {
        "id": part.id,
        "part_index": part.part_index,
        "page_number": part.page_number,
        "heading": part.heading,
        "text": part.text,
        "source_location": part.source_location,
    }


def _validate_metadata(principal: AuthPrincipal, request: Request, region: str | None) -> None:
    _ensure_document_scope(principal, request, region)


def _ensure_document_scope(principal: AuthPrincipal, request: Request, region: str | None) -> None:
    if region is None and "*" not in principal.regions and "admin" not in principal.roles:
        raise _error(422, "REGION_REQUIRED", "区域用户上传文档时必须提供区域")
    ensure_region_access(principal, region, request)


async def upload_document(
    db: Session,
    settings: Settings,
    principal: AuthPrincipal,
    request: Request,
    upload: UploadFile,
    facility_type: str | None,
    region: str | None,
    effective_date: date | None,
    expiry_date: date | None,
    version: str,
    source_type: str,
) -> tuple[Document, list[DocumentPart]]:
    _validate_metadata(principal, request, region)
    if effective_date and expiry_date and expiry_date < effective_date:
        raise _error(422, "INVALID_DOCUMENT_DATES", "失效日期不能早于生效日期")
    try:
        filename = validate_filename(upload.filename)
        media_type = validate_media_type(filename, upload.content_type)
    except DocumentParseError as exc:
        code = str(exc)
        status = 400 if code != "UNSUPPORTED_EXTENSION" else 415
        raise _error(status, code, "上传文件名、扩展名或内容类型不被允许") from None
    content = await upload.read(settings.rag_max_upload_bytes + 1)
    if len(content) > settings.rag_max_upload_bytes:
        raise _error(413, "DOCUMENT_TOO_LARGE", "文档超过大小限制")
    digest = hashlib.sha256(content).hexdigest()
    existing = db.scalar(select(Document).where(Document.sha256 == digest, Document.is_deleted.is_(False)))
    if existing is not None:
        _ensure_document_scope(principal, request, existing.region)
        raise _error(409, "DUPLICATE_DOCUMENT", "相同文档已上传", document_id=existing.id)
    extension = Path(filename).suffix.lower()
    document_id = f"DOC-{uuid4().hex[:16].upper()}"
    relative_key = f"{document_id}/{filename}"
    storage_root = Path(settings.rag_storage_directory).resolve()
    target = (storage_root / document_id / filename).resolve()
    if storage_root not in target.parents:
        raise _error(400, "UNSAFE_STORAGE_PATH", "文档存储路径无效")
    now = datetime.now().astimezone().replace(tzinfo=None)
    document = Document(
        id=document_id,
        original_filename=filename,
        storage_key=relative_key,
        media_type=media_type,
        extension=extension,
        size_bytes=len(content),
        sha256=digest,
        status="UPLOADING",
        uploaded_by=principal.subject,
        facility_type=facility_type,
        region=region,
        effective_date=effective_date,
        expiry_date=expiry_date,
        version=version,
        source_type=source_type,
        source_system="municipal-facility-ops",
        created_at=now,
        updated_at=now,
    )
    db.add(document)
    db.commit()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, target)
        parsed = parse_document(filename, content)
        parts = [
            DocumentPart(
                id=f"PART-{uuid4().hex[:16].upper()}",
                document_id=document.id,
                part_index=index,
                page_number=part.page_number,
                heading=part.heading,
                text=part.text,
                source_location=part.source_location,
                created_at=now,
            )
            for index, part in enumerate(parsed)
        ]
        db.add_all(parts)
        document.status = "PARSED"
        document.updated_at = datetime.now().astimezone().replace(tzinfo=None)
        db.commit()
        db.refresh(document)
        record_security_event(
            "document_uploaded_and_parsed",
            request=request,
            subject=principal.subject,
            details={"document_id": document.id, "parts": len(parts)},
        )
        return document, parts
    except DocumentParseError as exc:
        db.rollback()
        document = db.get(Document, document_id)
        if document is None:
            raise _error(422, "DOCUMENT_PARSE_FAILED", "文档解析失败") from None
        document.status = "FAILED"
        document.error_reason = str(exc)
        document.updated_at = datetime.now().astimezone().replace(tzinfo=None)
        db.commit()
        record_security_event(
            "document_parse_failed",
            request=request,
            subject=principal.subject,
            details={"document_id": document.id, "reason": str(exc)},
        )
        raise _error(422, "DOCUMENT_PARSE_FAILED", "文档解析失败", document_id=document.id) from None
    except Exception:
        db.rollback()
        if temporary.exists():
            temporary.unlink(missing_ok=True)
        failed = db.get(Document, document_id)
        if failed is not None:
            failed.status = "FAILED"
            failed.error_reason = "DOCUMENT_STORAGE_OR_PROCESSING_ERROR"
            failed.updated_at = datetime.now().astimezone().replace(tzinfo=None)
            db.commit()
        raise


def list_documents(
    db: Session,
    principal: AuthPrincipal,
    request: Request,
    page: int,
    page_size: int,
    status: str | None = None,
    region: str | None = None,
    facility_type: str | None = None,
    version: str | None = None,
) -> dict:
    from sqlalchemy import func

    ensure_region_access(principal, region, request)
    stmt = select(Document).where(Document.is_deleted.is_(False))
    if "*" not in principal.regions and "admin" not in principal.roles:
        stmt = stmt.where(
            Document.region.in_(sorted(principal.regions)) if principal.regions else Document.id == "__none__"
        )
    if region:
        stmt = stmt.where(Document.region == region)
    if status:
        stmt = stmt.where(Document.status == status)
    if facility_type:
        stmt = stmt.where(Document.facility_type == facility_type)
    if version:
        stmt = stmt.where(Document.version == version)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Document.created_at.desc(), Document.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {"items": [document_dict(row) for row in rows], "total": total, "page": page, "page_size": page_size}


def get_document(
    db: Session, principal: AuthPrincipal, request: Request, document_id: str
) -> tuple[Document, list[DocumentPart]]:
    document = db.get(Document, document_id)
    if document is None or document.is_deleted:
        raise _error(404, "DOCUMENT_NOT_FOUND", "文档不存在")
    if (
        document.region is None
        and principal.regions
        and "*" not in principal.regions
        and "admin" not in principal.roles
    ):
        raise _error(403, "REGION_SCOPE_DENIED", "超出用户区域范围")
    ensure_region_access(principal, document.region, request)
    parts = db.scalars(
        select(DocumentPart).where(DocumentPart.document_id == document.id).order_by(DocumentPart.part_index)
    ).all()
    return document, parts
