from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentPartResponse(BaseModel):
    id: str
    part_index: int
    page_number: int | None
    heading: str | None
    text: str
    source_location: str | None


class DocumentResponse(BaseModel):
    id: str
    original_filename: str
    storage_key: str
    media_type: str
    extension: str
    size_bytes: int
    sha256: str
    status: str
    error_reason: str | None
    uploaded_by: str
    facility_type: str | None
    region: str | None
    effective_date: date | None
    expiry_date: date | None
    version: str
    source_type: str
    source_system: str
    created_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class DocumentDetailResponse(BaseModel):
    item: DocumentResponse
    parts: list[DocumentPartResponse]


class ChunkResponse(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    text: str
    token_count: int
    page_number: int | None
    heading: str | None
    source_part_id: str | None
    start_offset: int
    end_offset: int
    target_tokens: int
    overlap_tokens: int
    cleaning_version: str


class ChunkPreviewResponse(BaseModel):
    items: list[ChunkResponse]
    target_tokens: int
    overlap_tokens: int


class ChunkRegenerateRequest(BaseModel):
    target_tokens: int = 800
    overlap_tokens: int = 120


class EmbeddingResponse(BaseModel):
    status: str
    batch_id: str
    document_id: str
    model: str
    chunk_count: int
    embedded_count: int
    attempt_count: int


class RagSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    facility_type: str | None = Field(default=None, max_length=64)
    region: str | None = Field(default=None, max_length=100)
    version: str | None = Field(default=None, max_length=64)
    as_of_date: date | None = None
    top_k: int = Field(default=5, ge=1, le=50)
    rerank: bool = False


class RagSearchItem(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int | None
    similarity: float
    snippet: str
    metadata: dict[str, Any]


class RagSearchResponse(BaseModel):
    status: str
    message: str | None
    query: str
    rewritten_query: str
    filters: dict[str, Any]
    items: list[RagSearchItem]
    warnings: list[str] = Field(default_factory=list)


class RagSearchDebugResponse(RagSearchResponse):
    debug: dict[str, Any]
