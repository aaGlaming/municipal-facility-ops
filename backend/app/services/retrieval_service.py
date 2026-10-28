"""Hybrid RAG retrieval with deterministic query rewriting and source snippets."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date
from typing import Any

from fastapi import HTTPException, Request
from sqlalchemy import and_, false, or_, select
from sqlalchemy.orm import Session

from app.core.auth import AuthPrincipal, ensure_region_access
from app.core.config import Settings
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.rag import reranker
from app.schemas.rag import RagSearchRequest
from app.services import embedding_service
from app.services.audit_service import record_security_event

MAX_QUERY_TERMS = 12
MAX_VECTOR_CANDIDATES = 100
STOP_WORDS = {"the", "and", "for", "with", "from", "this", "that", "请", "查询", "一下", "相关"}
FACILITY_TYPES = {
    "street_light",
    "traffic_signal",
    "road_damage",
    "manhole",
    "sidewalk",
    "drainage",
    "waste_facility",
    "greenery",
}


@dataclass(frozen=True)
class QueryRewrite:
    text: str
    facility_type: str | None
    region: str | None
    version: str | None
    as_of_date: date | None
    terms: list[str]


def _error(status_code: int, code: str, message: str, *, retryable: bool = False, **extra: object) -> HTTPException:
    detail: dict[str, object] = {"code": code, "message": message, "retryable": retryable}
    detail.update(extra)
    return HTTPException(status_code=status_code, detail=detail)


def _permission(principal: AuthPrincipal, request: Request) -> None:
    if not principal.has_permission("document:read"):
        record_security_event(
            "permission_denied", request=request, subject=principal.subject, details={"permission": "document:read"}
        )
        raise _error(403, "PERMISSION_DENIED", "没有执行该操作的权限")


def _terms(value: str) -> list[str]:
    values = re.findall(r"[A-Za-z0-9_:-]+|[\u3400-\u9fff]+", value.lower())
    return [value for value in values if value not in STOP_WORDS][:MAX_QUERY_TERMS]


def rewrite_query(payload: RagSearchRequest) -> QueryRewrite:
    text = re.sub(r"\s+", " ", payload.query.strip())
    lower = text.lower()
    facility_type = payload.facility_type
    if facility_type is None:
        facility_type = next((value for value in FACILITY_TYPES if value in lower), None)
    region = payload.region
    if region is None:
        match = re.search(r"\b(?:district|region)[-_][a-z0-9_-]+\b", lower, re.IGNORECASE)
        region = match.group(0).upper() if match else None
    version = payload.version
    if version is None:
        match = re.search(r"\bv\d+(?:\.\d+)*\b", lower, re.IGNORECASE)
        version = match.group(0) if match else None
    as_of_date = payload.as_of_date
    if as_of_date is None:
        match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
        if match:
            try:
                as_of_date = date.fromisoformat(match.group(1))
            except ValueError:
                as_of_date = None
    return QueryRewrite(text, facility_type, region, version, as_of_date or date.today(), _terms(text))


def _base_conditions(rewrite: QueryRewrite, principal: AuthPrincipal) -> list[Any]:
    conditions: list[Any] = [
        DocumentChunk.document_id == Document.id,
        Document.status == "PARSED",
        Document.is_deleted.is_(False),
        DocumentChunk.embedding_status == "INDEXED",
        or_(Document.effective_date.is_(None), Document.effective_date <= rewrite.as_of_date),
        or_(Document.expiry_date.is_(None), Document.expiry_date >= rewrite.as_of_date),
    ]
    if rewrite.facility_type:
        conditions.append(Document.facility_type == rewrite.facility_type)
    if rewrite.region:
        conditions.append(Document.region == rewrite.region)
    elif "*" not in principal.regions and "admin" not in principal.roles:
        conditions.append(Document.region.in_(sorted(principal.regions)) if principal.regions else false())
    if rewrite.version:
        conditions.append(Document.version == rewrite.version)
    return conditions


def _keyword_rows(db: Session, rewrite: QueryRewrite, principal: AuthPrincipal) -> list[tuple[DocumentChunk, Document]]:
    conditions = _base_conditions(rewrite, principal)
    if rewrite.terms:
        conditions.append(or_(*[DocumentChunk.text.ilike(f"%{term}%") for term in rewrite.terms]))
    statement = (
        select(DocumentChunk, Document)
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(and_(*conditions))
    )
    return list(db.execute(statement.limit(MAX_VECTOR_CANDIDATES)).all())


def _chunk_rows(db: Session, ids: set[str]) -> dict[str, tuple[DocumentChunk, Document]]:
    if not ids:
        return {}
    statement = (
        select(DocumentChunk, Document)
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(DocumentChunk.id.in_(ids))
    )
    return {chunk.id: (chunk, document) for chunk, document in db.execute(statement).all()}


def _keyword_score(chunk: DocumentChunk, terms: list[str]) -> float:
    if not terms:
        return 0.0
    content = f"{chunk.heading or ''} {chunk.text}".lower()
    return min(1.0, sum(content.count(term) for term in terms) / max(1, len(terms) * 2))


def _snippet(text: str, terms: list[str]) -> str:
    limit = 480
    if len(text) <= limit:
        return text
    lower = text.lower()
    start = min((lower.find(term) for term in terms if lower.find(term) >= 0), default=0)
    left = max(0, start - 160)
    value = text[left : left + limit]
    return ("…" if left else "") + value + ("…" if left + limit < len(text) else "")


def _flatten(value: Any) -> list[Any]:
    if isinstance(value, list) and value and isinstance(value[0], list):
        return value[0]
    return value if isinstance(value, list) else []


def _filters(rewrite: QueryRewrite) -> dict[str, Any]:
    return {
        "facility_type": rewrite.facility_type,
        "region": rewrite.region,
        "version": rewrite.version,
        "as_of_date": rewrite.as_of_date,
    }


def _can_view_document(principal: AuthPrincipal, document: Document) -> bool:
    if "*" in principal.regions or "admin" in principal.roles:
        return True
    return document.region is not None and document.region in principal.regions


def _chroma_where(rewrite: QueryRewrite, principal: AuthPrincipal, model: str) -> dict[str, Any]:
    filters: list[dict[str, Any]] = [{"embedding_model": {"$eq": model}}]
    if rewrite.facility_type:
        filters.append({"facility_type": {"$eq": rewrite.facility_type}})
    if rewrite.region:
        filters.append({"region": {"$eq": rewrite.region}})
    elif "*" not in principal.regions and "admin" not in principal.roles and len(principal.regions) == 1:
        filters.append({"region": {"$eq": next(iter(principal.regions))}})
    if rewrite.version:
        filters.append({"version": {"$eq": rewrite.version}})
    return filters[0] if len(filters) == 1 else {"$and": filters}


def search_documents(
    db: Session,
    settings: Settings,
    principal: AuthPrincipal,
    request: Request,
    payload: RagSearchRequest,
    *,
    debug: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    _permission(principal, request)
    rewrite = rewrite_query(payload)
    if rewrite.region:
        ensure_region_access(principal, rewrite.region, request)

    if not rewrite.terms:
        result: dict[str, Any] = {
            "status": "NO_RECALL",
            "message": "查询未包含可检索词",
            "query": payload.query,
            "rewritten_query": rewrite.text,
            "filters": _filters(rewrite),
            "items": [],
            "warnings": [],
        }
        if debug:
            result["debug"] = {
                "keyword_count": 0,
                "vector_count": 0,
                "merged_count": 0,
                "returned_count": 0,
                "vector_model": None,
                "vector_error": None,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            }
        return result

    keyword_rows = _keyword_rows(db, rewrite, principal) if rewrite.terms else []
    rows_by_id = {chunk.id: (chunk, document) for chunk, document in keyword_rows}
    vector_scores: dict[str, float] = {}
    warnings: list[str] = []
    provider_model: str | None = None
    vector_count = 0
    vector_error: str | None = None
    try:
        provider = embedding_service.get_embedding_provider(settings)
        provider_model = provider.model
        keyword_rows = [row for row in keyword_rows if row[0].embedding_model == provider_model]
        rows_by_id = {chunk.id: (chunk, document) for chunk, document in keyword_rows}
        cache = embedding_service.EmbeddingCache(settings.embedding_cache_directory)
        query_vector = cache.get(provider_model, rewrite.text)
        if query_vector is None:
            embedding_service._get_rate_limiter(settings.embedding_rate_limit_per_minute).wait()
            query_vectors = provider.embed_texts([rewrite.text])
            if len(query_vectors) != 1:
                raise embedding_service.EmbeddingProviderError("query embedding result is incomplete", retryable=True)
            query_vector = query_vectors[0]
            cache.put(provider_model, rewrite.text, query_vector)
        chroma = embedding_service.get_chroma_store(settings)
        result = chroma.query(
            embedding=query_vector,
            n_results=min(max(payload.top_k * 4, 20), MAX_VECTOR_CANDIDATES),
            where=_chroma_where(rewrite, principal, provider_model),
        )
        ids = _flatten(result.get("ids"))
        distances = _flatten(result.get("distances"))
        vector_count = len(ids)
        vector_rows = _chunk_rows(db, {str(value) for value in ids})
        for index, raw_id in enumerate(ids):
            chunk_id = str(raw_id)
            row = vector_rows.get(chunk_id)
            if row is None:
                continue
            chunk, document = row
            if (
                chunk.embedding_status != "INDEXED"
                or chunk.embedding_model != provider_model
                or document.status != "PARSED"
                or document.is_deleted
            ):
                continue
            if rewrite.facility_type and document.facility_type != rewrite.facility_type:
                continue
            if rewrite.region and document.region != rewrite.region:
                continue
            if rewrite.version and document.version != rewrite.version:
                continue
            if not _can_view_document(principal, document):
                continue
            if not (
                (document.effective_date is None or document.effective_date <= rewrite.as_of_date)
                and (document.expiry_date is None or document.expiry_date >= rewrite.as_of_date)
            ):
                continue
            distance = float(distances[index]) if index < len(distances) else 1.0
            vector_scores[chunk_id] = max(0.0, min(1.0, 1.0 - distance))
            rows_by_id.setdefault(chunk_id, row)
    except embedding_service.EmbeddingProviderError as exc:
        vector_error = str(exc)
        warnings.append("向量检索暂不可用，已使用关键词召回" if keyword_rows else "向量检索服务不可用")
    except Exception:
        vector_error = "vector retrieval failed"
        warnings.append("向量检索暂不可用，已使用关键词召回" if keyword_rows else "向量检索服务不可用")

    if not rows_by_id:
        if vector_error and not keyword_rows:
            raise _error(503, "RETRIEVAL_UNAVAILABLE", "检索服务暂不可用，请稍后重试", retryable=True)
        message = "没有找到当前生效且已完成索引的文档片段"
        result: dict[str, Any] = {
            "status": "NO_RECALL",
            "message": message,
            "query": payload.query,
            "rewritten_query": rewrite.text,
            "filters": _filters(rewrite),
            "items": [],
            "warnings": warnings,
        }
        if debug:
            result["debug"] = {
                "keyword_count": len(keyword_rows),
                "vector_count": vector_count,
                "merged_count": 0,
                "vector_model": provider_model,
                "vector_error": vector_error,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            }
        return result

    keyword_scores = {chunk.id: _keyword_score(chunk, rewrite.terms) for chunk, _ in keyword_rows}
    scored: list[tuple[float, DocumentChunk, Document]] = []
    for chunk_id, (chunk, document) in rows_by_id.items():
        vector_score = vector_scores.get(chunk_id, 0.0)
        keyword_score = keyword_scores.get(chunk_id, _keyword_score(chunk, rewrite.terms))
        score = 0.7 * vector_score + 0.3 * keyword_score if vector_scores else keyword_score
        scored.append((min(1.0, score), chunk, document))
    scored.sort(key=lambda value: (-value[0], value[1].chunk_index))
    if payload.rerank:
        try:
            provider = reranker.get_rerank_provider(settings)
            rerank_results = provider.rerank(
                rewrite.text,
                [chunk.text for _, chunk, _ in scored],
                len(scored),
            )
            score_by_index = {index: score for index, score in rerank_results}
            scored = [
                (max(0.0, min(1.0, score_by_index[index])), chunk, document)
                for index, (_, chunk, document) in enumerate(scored)
                if index in score_by_index
            ]
            scored.sort(key=lambda value: (-value[0], value[1].chunk_index))
        except reranker.RerankProviderError:
            warnings.append("重排模型暂不可用，已使用向量与关键词排序")
    items: list[dict[str, Any]] = []
    for score, chunk, document in scored[: payload.top_k]:
        items.append(
            {
                "chunk_id": chunk.id,
                "document_id": document.id,
                "document_name": document.original_filename,
                "page_number": chunk.page_number,
                "similarity": round(score, 6),
                "snippet": _snippet(chunk.text, rewrite.terms),
                "metadata": {
                    "document_id": document.id,
                    "document_version": f"{document.version}:{document.updated_at.isoformat()}",
                    "chunk_id": chunk.id,
                    "chunk_index": chunk.chunk_index,
                    "page_number": chunk.page_number,
                    "heading": chunk.heading,
                    "facility_type": document.facility_type,
                    "region": document.region,
                    "version": document.version,
                    "effective_date": document.effective_date,
                    "expiry_date": document.expiry_date,
                    "source_type": document.source_type,
                    "embedding_model": chunk.embedding_model,
                    "similarity": round(score, 6),
                },
            }
        )
    result = {
        "status": "OK" if not warnings else "PARTIAL",
        "message": None,
        "query": payload.query,
        "rewritten_query": rewrite.text,
        "filters": _filters(rewrite),
        "items": items,
        "warnings": warnings,
    }
    if debug:
        result["debug"] = {
            "keyword_count": len(keyword_rows),
            "vector_count": vector_count,
            "merged_count": len(scored),
            "returned_count": len(items),
            "vector_model": provider_model,
            "vector_error": vector_error,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        }
    return result
