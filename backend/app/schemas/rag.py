from datetime import date, datetime

from pydantic import BaseModel


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
