"""Text cleaning and deterministic document chunk generation."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException, Request
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.auth import AuthPrincipal
from app.models.chunk import DocumentChunk
from app.models.document import DocumentPart
from app.services.document_service import get_document

MAX_CHUNKS_PER_DOCUMENT = 10_000


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message, "retryable": False})


def _validate_parameters(target_tokens: int, overlap_tokens: int) -> None:
    if target_tokens < 20 or target_tokens > 4000:
        raise _error(422, "INVALID_CHUNK_PARAMETERS", "target_tokens 必须在 20 到 4000 之间")
    if overlap_tokens < 0 or overlap_tokens >= target_tokens:
        raise _error(422, "INVALID_CHUNK_PARAMETERS", "overlap_tokens 必须小于 target_tokens")


def approximate_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def clean_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(
        r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f\u061c\u200b\u200c\u200d\u200e\u200f\u202a-\u202e\u2066-\u2069\ufeff]",
        "",
        normalized,
    )
    lines: list[str] = []
    for line in normalized.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        if not line or re.fullmatch(r"[-–—]?\s*\d+\s*[-–—]?", line):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _clean_parts(parts: list[DocumentPart]) -> list[tuple[DocumentPart, str]]:
    line_counts = Counter(
        line.strip() for part in parts for line in part.text.splitlines() if line.strip() and len(line.strip()) <= 160
    )
    repeated_lines = {line for line, count in line_counts.items() if count >= 2}
    cleaned: list[tuple[DocumentPart, str]] = []
    for part in parts:
        source = "\n".join(line for line in part.text.splitlines() if line.strip() not in repeated_lines)
        value = clean_text(source)
        if value:
            cleaned.append((part, value))
    return cleaned


def _split_block(text: str, target_chars: int, overlap_chars: int) -> list[tuple[str, int, int]]:
    if len(text) <= target_chars:
        return [(text, 0, len(text))]
    chunks: list[tuple[str, int, int]] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + target_chars)
        if end < len(text):
            boundary = max(
                text.rfind("\n", start + target_chars // 2, end), text.rfind(". ", start + target_chars // 2, end)
            )
            if boundary > start:
                end = boundary + (2 if text[boundary : boundary + 2] == ". " else 1)
        chunks.append((text[start:end].strip(), start, end))
        if end >= len(text):
            break
        start = max(start + 1, end - overlap_chars)
    return chunks


def preview_chunks(
    db: Session,
    principal: AuthPrincipal,
    request: Request,
    document_id: str,
    target_tokens: int,
    overlap_tokens: int,
) -> tuple[list[dict], int, int]:
    _validate_parameters(target_tokens, overlap_tokens)
    document, parts = get_document(db, principal, request, document_id)
    target_chars = target_tokens * 4
    overlap_chars = overlap_tokens * 4
    cleaned_parts = _clean_parts(parts)
    step_chars = max(1, target_chars - overlap_chars)
    estimated_chunks = sum(max(1, math.ceil((len(text) - overlap_chars) / step_chars)) for _, text in cleaned_parts)
    if estimated_chunks > MAX_CHUNKS_PER_DOCUMENT:
        raise _error(422, "CHUNK_LIMIT_EXCEEDED", "文档生成的 Chunk 数量超过上限")
    items: list[dict] = []
    index = 0
    for part, text in cleaned_parts:
        for chunk_text, start, end in _split_block(text, target_chars, overlap_chars):
            items.append(
                {
                    "id": f"PREVIEW-{index:04d}",
                    "document_id": document.id,
                    "chunk_index": index,
                    "text": chunk_text,
                    "token_count": approximate_tokens(chunk_text),
                    "page_number": part.page_number,
                    "heading": part.heading,
                    "source_part_id": part.id,
                    "start_offset": start,
                    "end_offset": end,
                    "target_tokens": target_tokens,
                    "overlap_tokens": overlap_tokens,
                    "cleaning_version": "step15-v1",
                }
            )
            index += 1
    return items, target_tokens, overlap_tokens


def persisted_chunks(
    db: Session, principal: AuthPrincipal, request: Request, document_id: str
) -> tuple[list[dict], int, int]:
    document, _ = get_document(db, principal, request, document_id)
    rows = db.scalars(
        select(DocumentChunk).where(DocumentChunk.document_id == document.id).order_by(DocumentChunk.chunk_index)
    ).all()
    if not rows:
        return [], 0, 0
    return [chunk_dict(row) for row in rows], rows[0].target_tokens, rows[0].overlap_tokens


def regenerate_chunks(
    db: Session,
    principal: AuthPrincipal,
    request: Request,
    document_id: str,
    target_tokens: int,
    overlap_tokens: int,
) -> tuple[list[dict], int, int]:
    _validate_parameters(target_tokens, overlap_tokens)
    items, _, _ = preview_chunks(db, principal, request, document_id, target_tokens, overlap_tokens)
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
    now = datetime.now().astimezone().replace(tzinfo=None)
    rows = [DocumentChunk(**{**item, "id": f"CHUNK-{uuid4().hex[:16].upper()}", "created_at": now}) for item in items]
    db.add_all(rows)
    db.commit()
    return [chunk_dict(row) for row in rows], target_tokens, overlap_tokens


def chunk_dict(chunk: DocumentChunk) -> dict:
    return {
        "id": chunk.id,
        "document_id": chunk.document_id,
        "chunk_index": chunk.chunk_index,
        "text": chunk.text,
        "token_count": chunk.token_count,
        "page_number": chunk.page_number,
        "heading": chunk.heading,
        "source_part_id": chunk.source_part_id,
        "start_offset": chunk.start_offset,
        "end_offset": chunk.end_offset,
        "target_tokens": chunk.target_tokens,
        "overlap_tokens": chunk.overlap_tokens,
        "cleaning_version": chunk.cleaning_version,
    }
