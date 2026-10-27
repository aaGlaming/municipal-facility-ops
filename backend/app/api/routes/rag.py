from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.core.auth import AuthPrincipal, require_permission
from app.core.config import Settings
from app.core.dependencies import get_db_session, get_settings_dependency
from app.schemas.rag import (
    ChunkPreviewResponse,
    ChunkRegenerateRequest,
    DocumentDetailResponse,
    EmbeddingResponse,
    RagSearchDebugResponse,
    RagSearchRequest,
    RagSearchResponse,
)
from app.services.chunk_service import persisted_chunks, preview_chunks, regenerate_chunks
from app.services.document_service import document_dict, get_document, part_dict, upload_document
from app.services.embedding_service import delete_document_embeddings, rebuild_document_embeddings
from app.services.retrieval_service import search_documents

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/search", response_model=RagSearchResponse)
def search(
    payload: RagSearchRequest,
    request: Request,
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dependency),
    principal: AuthPrincipal = Depends(require_permission("document:read")),
) -> dict:
    return search_documents(db, settings, principal, request, payload)


@router.post("/search/debug", response_model=RagSearchDebugResponse)
def search_debug(
    payload: RagSearchRequest,
    request: Request,
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dependency),
    principal: AuthPrincipal = Depends(require_permission("document:read")),
) -> dict:
    return search_documents(db, settings, principal, request, payload, debug=True)


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


@router.get("/documents/{document_id}/chunks/preview", response_model=ChunkPreviewResponse)
def preview(
    document_id: str,
    request: Request,
    target_tokens: int | None = Query(default=None, ge=20, le=4000),
    overlap_tokens: int | None = Query(default=None, ge=0, lt=4000),
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dependency),
    principal: AuthPrincipal = Depends(require_permission("document:read")),
) -> dict:
    target = target_tokens if target_tokens is not None else settings.rag_chunk_target_tokens
    overlap = overlap_tokens if overlap_tokens is not None else settings.rag_chunk_overlap_tokens
    items, target, overlap = preview_chunks(db, principal, request, document_id, target, overlap)
    if overlap >= target:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_CHUNK_PARAMETERS",
                "message": "overlap_tokens 必须小于 target_tokens",
                "retryable": False,
            },
        )
    return {"items": items, "target_tokens": target, "overlap_tokens": overlap}


@router.post("/documents/{document_id}/chunks/regenerate", response_model=ChunkPreviewResponse)
def regenerate(
    document_id: str,
    payload: ChunkRegenerateRequest,
    request: Request,
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("document:chunk")),
) -> dict:
    items, target, overlap = regenerate_chunks(
        db, principal, request, document_id, payload.target_tokens, payload.overlap_tokens
    )
    return {"items": items, "target_tokens": target, "overlap_tokens": overlap}


@router.get("/documents/{document_id}/chunks", response_model=ChunkPreviewResponse)
def chunks(
    document_id: str,
    request: Request,
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("document:read")),
) -> dict:
    items, target, overlap = persisted_chunks(db, principal, request, document_id)
    return {"items": items, "target_tokens": target, "overlap_tokens": overlap}


@router.post("/documents/{document_id}/embeddings/rebuild", response_model=EmbeddingResponse)
def rebuild_embeddings(
    document_id: str,
    request: Request,
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dependency),
    principal: AuthPrincipal = Depends(require_permission("document:embed")),
) -> dict:
    return rebuild_document_embeddings(db, settings, principal, request, document_id)


@router.delete("/documents/{document_id}/embeddings", response_model=dict)
def delete_embeddings(
    document_id: str,
    request: Request,
    db: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings_dependency),
    principal: AuthPrincipal = Depends(require_permission("document:embed")),
) -> dict:
    return delete_document_embeddings(db, settings, principal, request, document_id)
