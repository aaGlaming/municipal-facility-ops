"""Embedding generation, caching and Chroma persistence for RAG chunks."""

from __future__ import annotations

import hashlib
import json
import math
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import AuthPrincipal
from app.core.config import Settings
from app.models.chunk import DocumentChunk
from app.models.embedding import EmbeddingBatch
from app.services.audit_service import record_security_event
from app.services.document_service import get_document


class EmbeddingProviderError(RuntimeError):
    """An embedding provider or vector store operation failed."""

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


def _error(status_code: int, code: str, message: str, *, retryable: bool = False, **extra: object) -> HTTPException:
    detail: dict[str, object] = {"code": code, "message": message, "retryable": retryable}
    detail.update(extra)
    return HTTPException(status_code=status_code, detail=detail)


def _permission(principal: AuthPrincipal, request: Request) -> None:
    if not principal.has_permission("document:embed"):
        record_security_event(
            "permission_denied", request=request, subject=principal.subject, details={"permission": "document:embed"}
        )
        raise _error(403, "PERMISSION_DENIED", "没有执行该操作的权限")


class EmbeddingProvider:
    """OpenAI compatible embedding client with bounded retries and timeout."""

    def __init__(self, settings: Settings) -> None:
        if settings.llm_api_key in {"", "replace_me"} or settings.embedding_model in {"", "replace_me"}:
            raise EmbeddingProviderError("embedding model is not configured", retryable=False)
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency is supplied in deployment image
            raise EmbeddingProviderError("OpenAI client is unavailable", retryable=False) from exc
        self.model = settings.embedding_model
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=settings.embedding_timeout_seconds,
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        attempts = self._settings.embedding_max_retries + 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                response = self._client.embeddings.create(model=self.model, input=texts)
                items = sorted(response.data, key=lambda item: item.index)
                vectors = [list(item.embedding) for item in items]
                if len(vectors) != len(texts):
                    raise ValueError("embedding provider returned an unexpected item count")
                return vectors
            except Exception as exc:  # provider SDKs expose different exception types
                last_error = exc
                if attempt + 1 < attempts:
                    time.sleep(min(2**attempt, 8))
        raise EmbeddingProviderError("embedding provider request failed", retryable=True) from last_error


class EmbeddingCache:
    """Small file cache keyed by model and exact chunk text."""

    def __init__(self, directory: str) -> None:
        self.directory = Path(directory)
        self._lock = threading.Lock()

    @staticmethod
    def key(model: str, text: str) -> str:
        return hashlib.sha256(f"{model}\0{text}".encode("utf-8")).hexdigest()

    def get(self, model: str, text: str) -> list[float] | None:
        path = self.directory / f"{self.key(model, text)}.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return None
        if isinstance(value, list) and all(isinstance(item, (int, float)) for item in value):
            return [float(item) for item in value]
        return None

    def put(self, model: str, text: str, vector: list[float]) -> None:
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            path = self.directory / f"{self.key(model, text)}.json"
            temporary = path.with_suffix(f".{uuid4().hex}.tmp")
            with self._lock:
                temporary.write_text(json.dumps(vector, separators=(",", ":")), encoding="utf-8")
                temporary.replace(path)
        except OSError:
            # Cache persistence is an optimization; a read-only cache must not
            # turn a successfully generated vector into a failed indexing job.
            return


class RateLimiter:
    def __init__(self, limit_per_minute: int) -> None:
        self.limit = limit_per_minute
        self.calls: deque[float] = deque()
        self._lock = threading.Lock()

    def wait(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                while self.calls and now - self.calls[0] >= 60:
                    self.calls.popleft()
                if len(self.calls) < self.limit:
                    self.calls.append(now)
                    return
                delay = max(0.01, 60 - (now - self.calls[0]))
            time.sleep(delay)


_rate_limiter_lock = threading.Lock()
_rate_limiters: dict[int, RateLimiter] = {}


def _get_rate_limiter(limit_per_minute: int) -> RateLimiter:
    with _rate_limiter_lock:
        limiter = _rate_limiters.get(limit_per_minute)
        if limiter is None:
            limiter = RateLimiter(limit_per_minute)
            _rate_limiters[limit_per_minute] = limiter
        return limiter


class ChromaStore:
    def __init__(self, settings: Settings) -> None:
        try:
            import chromadb
        except ImportError as exc:  # pragma: no cover - deployment dependency
            raise EmbeddingProviderError("Chroma client is unavailable", retryable=True) from exc
        try:
            self._client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
            self._collection = self._client.get_or_create_collection(
                name=settings.chroma_collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as exc:  # pragma: no cover - requires running Chroma service
            raise EmbeddingProviderError("Chroma collection is unavailable", retryable=True) from exc

    def upsert(
        self,
        *,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        try:
            self._collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        except Exception as exc:  # pragma: no cover - requires running Chroma service
            raise EmbeddingProviderError("Chroma upsert failed", retryable=True) from exc

    def delete(self, ids: list[str]) -> None:
        if not ids:
            return
        try:
            self._collection.delete(ids=ids)
        except Exception as exc:  # pragma: no cover - requires running Chroma service
            raise EmbeddingProviderError("Chroma delete failed", retryable=True) from exc

    def query(self, *, embedding: list[float], n_results: int, where: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            arguments: dict[str, Any] = {"query_embeddings": [embedding], "n_results": n_results}
            if where:
                arguments["where"] = where
            return self._collection.query(**arguments)
        except Exception as exc:  # pragma: no cover - requires running Chroma service
            raise EmbeddingProviderError("Chroma query failed", retryable=True) from exc


def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    return EmbeddingProvider(settings)


def get_chroma_store(settings: Settings) -> ChromaStore:
    return ChromaStore(settings)


def _document_version(document: Any) -> str:
    return f"{document.version}:{document.updated_at.isoformat()}"


def _metadata(document: Any, chunk: DocumentChunk, model: str, batch_id: str) -> dict[str, Any]:
    return {
        "document_id": document.id,
        "document_version": _document_version(document),
        "chunk_id": chunk.id,
        "chunk_index": chunk.chunk_index,
        "page_number": chunk.page_number if chunk.page_number is not None else -1,
        "heading": chunk.heading or "",
        "facility_type": document.facility_type or "",
        "region": document.region or "",
        "effective_date": document.effective_date.isoformat() if document.effective_date else "",
        "expiry_date": document.expiry_date.isoformat() if document.expiry_date else "",
        "source_type": document.source_type,
        "version": document.version,
        "embedding_model": model,
        "embedding_batch_id": batch_id,
    }


def _mark_batch_failed(db: Session, batch_id: str, exc: Exception) -> bool:
    retryable = exc.retryable if isinstance(exc, EmbeddingProviderError) else True
    db.rollback()
    failed = db.get(EmbeddingBatch, batch_id)
    if failed is None:
        return retryable
    failed.status = "FAILED_RETRYABLE" if retryable else "FAILED"
    failed.error_reason = str(exc)[:1000]
    failed.retryable = retryable
    failed.finished_at = datetime.now()
    db.commit()
    return retryable


def _validate_vector(vector: Any) -> list[float]:
    if not isinstance(vector, (list, tuple)) or not vector:
        raise EmbeddingProviderError("embedding vector is empty or invalid", retryable=True)
    if not all(isinstance(value, (int, float)) and math.isfinite(float(value)) for value in vector):
        raise EmbeddingProviderError("embedding vector contains invalid values", retryable=True)
    return [float(value) for value in vector]


def rebuild_document_embeddings(
    db: Session,
    settings: Settings,
    principal: AuthPrincipal,
    request: Request,
    document_id: str,
) -> dict[str, object]:
    _permission(principal, request)
    document, _ = get_document(db, principal, request, document_id)
    chunks = db.scalars(
        select(DocumentChunk).where(DocumentChunk.document_id == document.id).order_by(DocumentChunk.chunk_index)
    ).all()
    if not chunks:
        raise _error(409, "CHUNKS_NOT_READY", "文档尚未生成 Chunk")

    try:
        provider = get_embedding_provider(settings)
    except EmbeddingProviderError as exc:
        raise _error(503, "EMBEDDING_NOT_CONFIGURED", str(exc), retryable=exc.retryable) from None
    model = provider.model
    batch = EmbeddingBatch(
        id=f"EMB-{uuid4().hex[:16].upper()}",
        document_id=document.id,
        model_name=model,
        status="RUNNING",
        chunk_count=len(chunks),
        embedded_count=0,
        attempt_count=1,
        retryable=True,
        document_version=_document_version(document),
    )
    db.add(batch)
    db.commit()

    cache = EmbeddingCache(settings.embedding_cache_directory)
    limiter = _get_rate_limiter(settings.embedding_rate_limit_per_minute)
    vectors: list[list[float]] = []
    try:
        for offset in range(0, len(chunks), settings.embedding_batch_size):
            group = chunks[offset : offset + settings.embedding_batch_size]
            missing_texts: list[str] = []
            missing_indexes: list[int] = []
            group_vectors: list[list[float] | None] = []
            for chunk in group:
                cached = cache.get(model, chunk.text)
                if cached is not None:
                    try:
                        cached = _validate_vector(cached)
                    except EmbeddingProviderError:
                        cached = None
                group_vectors.append(cached)
            for index, vector in enumerate(group_vectors):
                if vector is None:
                    missing_indexes.append(index)
                    missing_texts.append(group[index].text)
            if missing_texts:
                limiter.wait()
                generated = provider.embed_texts(missing_texts)
                if len(generated) != len(missing_indexes):
                    raise EmbeddingProviderError("embedding provider returned an unexpected item count", retryable=True)
                for index, vector in zip(missing_indexes, generated):
                    normalized = _validate_vector(vector)
                    group_vectors[index] = normalized
                    cache.put(model, group[index].text, normalized)
            vectors.extend(vector for vector in group_vectors if vector is not None)
        if len(vectors) != len(chunks):
            raise EmbeddingProviderError("embedding result is incomplete", retryable=True)
    except Exception as exc:
        retryable = _mark_batch_failed(db, batch.id, exc)
        raise _error(503, "EMBEDDING_FAILED", "Embedding 生成失败", retryable=retryable, batch_id=batch.id) from None

    try:
        store = get_chroma_store(settings)
        store.upsert(
            ids=[chunk.id for chunk in chunks],
            embeddings=vectors,
            documents=[chunk.text for chunk in chunks],
            metadatas=[_metadata(document, chunk, model, batch.id) for chunk in chunks],
        )
    except Exception as exc:
        retryable = _mark_batch_failed(db, batch.id, exc)
        raise _error(503, "CHROMA_WRITE_FAILED", "向量库写入失败", retryable=retryable, batch_id=batch.id) from None

    for chunk in chunks:
        chunk.embedding_status = "INDEXED"
        chunk.embedding_batch_id = batch.id
        chunk.embedding_model = model
    batch.status = "INDEXED"
    batch.embedded_count = len(chunks)
    batch.finished_at = datetime.now()
    db.commit()
    return {
        "status": batch.status,
        "batch_id": batch.id,
        "document_id": document.id,
        "model": model,
        "chunk_count": len(chunks),
        "embedded_count": len(chunks),
        "attempt_count": batch.attempt_count,
    }


def delete_document_embeddings(
    db: Session,
    settings: Settings,
    principal: AuthPrincipal,
    request: Request,
    document_id: str,
) -> dict[str, object]:
    _permission(principal, request)
    document, _ = get_document(db, principal, request, document_id)
    chunks = db.scalars(
        select(DocumentChunk).where(DocumentChunk.document_id == document.id).order_by(DocumentChunk.chunk_index)
    ).all()
    ids = [chunk.id for chunk in chunks]
    if ids:
        try:
            get_chroma_store(settings).delete(ids)
        except Exception as exc:
            retryable = exc.retryable if isinstance(exc, EmbeddingProviderError) else True
            raise _error(503, "CHROMA_DELETE_FAILED", "向量删除失败", retryable=retryable) from None
        for chunk in chunks:
            chunk.embedding_status = "PENDING"
            chunk.embedding_batch_id = None
            chunk.embedding_model = None
        db.commit()
    return {"document_id": document.id, "deleted_count": len(ids)}
