"""Durable, scoped and redacted session memory store."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, Request
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.auth import AuthPrincipal, ensure_region_access
from app.models.session_memory import SessionMemory
from app.schemas.memory import MemoryAppend, MemoryContext, MemoryMessage

SENSITIVE_KEY_PARTS = ("password", "passwd", "token", "secret", "api_key", "authorization", "cookie")
BEARER_PATTERN = re.compile(r"(?i)\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]+")
JWT_PATTERN = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def redact_text(value: str) -> str:
    value = BEARER_PATTERN.sub("[REDACTED_TOKEN]", value)
    value = JWT_PATTERN.sub("[REDACTED_TOKEN]", value)
    value = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", value)
    value = re.sub(r"(?i)(password|passwd|token|secret|api[_-]?key)\s*[:=]\s*[^\s,;]+", r"\1=[REDACTED]", value)
    return value[:8000]


def redact(value: Any, *, key: str = "") -> Any:
    if any(part in key.casefold() for part in SENSITIVE_KEY_PARTS):
        return "[REDACTED]"
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {str(item_key): redact(item_value, key=str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [redact(item, key=key) for item in value[:50]]
    if isinstance(value, tuple):
        return [redact(item, key=key) for item in value[:50]]
    return value


def _access(principal: AuthPrincipal, row: SessionMemory, request: Request) -> None:
    if row.user_id != principal.subject and "admin" not in principal.roles and "*" not in principal.permissions:
        raise HTTPException(
            status_code=403, detail={"code": "MEMORY_USER_SCOPE_DENIED", "message": "无权访问该会话记忆"}
        )
    if row.roles and "admin" not in principal.roles and not set(row.roles).intersection(principal.roles):
        raise HTTPException(
            status_code=403, detail={"code": "MEMORY_ROLE_SCOPE_DENIED", "message": "当前角色不能访问该会话记忆"}
        )
    ensure_region_access(principal, row.region, request)


class SessionMemoryStore:
    """Append bounded context; intentionally does not write to a vector store."""

    def __init__(self, *, ttl_seconds: int = 86_400, max_messages: int = 20, max_items: int = 20) -> None:
        if ttl_seconds < 60 or max_messages < 2 or max_items < 1:
            raise ValueError("invalid memory limits")
        self.ttl_seconds = ttl_seconds
        self.max_messages = max_messages
        self.max_items = max_items

    def open(
        self,
        db: Session,
        principal: AuthPrincipal,
        request: Request,
        session_id: str,
        *,
        region: str | None = None,
        ttl_seconds: int | None = None,
    ) -> SessionMemory:
        if not session_id or len(session_id) > 128:
            raise HTTPException(status_code=422, detail={"code": "INVALID_SESSION_ID", "message": "会话 ID 无效"})
        ensure_region_access(principal, region, request)
        now = _now()
        rows = db.scalars(
            select(SessionMemory)
            .where(SessionMemory.session_id == session_id)
            .order_by(SessionMemory.updated_at.desc())
        ).all()
        for row in rows:
            if row.deleted_at is not None:
                continue
            _access(principal, row, request)
            if row.expires_at > now:
                return row
        row = SessionMemory(
            id=f"MEM-{uuid4().hex[:16].upper()}",
            session_id=session_id,
            user_id=principal.subject,
            roles=sorted(principal.roles),
            region=region,
            summary="",
            messages=[],
            evidence=[],
            tool_results=[],
            confirmations=[],
            version=1,
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds or self.ttl_seconds),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    def load(self, db: Session, principal: AuthPrincipal, request: Request, session_id: str) -> MemoryContext | None:
        row = self._latest(db, principal, request, session_id)
        if row is None or row.expires_at <= _now() or row.deleted_at is not None:
            return None
        return self._context(row)

    def append(
        self,
        db: Session,
        principal: AuthPrincipal,
        request: Request,
        session_id: str,
        payload: MemoryAppend,
    ) -> MemoryContext:
        row = self.open(db, principal, request, session_id)
        if payload.message is not None:
            messages = list(row.messages or [])
            message = payload.message.model_dump(mode="json")
            message["content"] = redact_text(message["content"])
            message["metadata"] = redact(message.get("metadata", {}))
            messages.append(message)
            if len(messages) > self.max_messages:
                archived = messages[: -self.max_messages]
                row.summary = self._roll_summary(row.summary, archived)
                messages = messages[-self.max_messages :]
            row.messages = redact(messages)
        row.evidence = self._bounded(row.evidence, payload.evidence)
        row.tool_results = self._bounded(row.tool_results, payload.tool_results)
        row.confirmations = self._bounded(row.confirmations, payload.confirmations)
        row.version += 1
        row.updated_at = _now()
        db.commit()
        db.refresh(row)
        return self._context(row)

    def delete(self, db: Session, principal: AuthPrincipal, request: Request, session_id: str) -> bool:
        row = self._latest(db, principal, request, session_id)
        if row is None or row.deleted_at is not None:
            return False
        row.deleted_at = _now()
        row.messages = []
        row.evidence = []
        row.tool_results = []
        row.confirmations = []
        row.summary = ""
        row.updated_at = _now()
        db.commit()
        return True

    def purge_expired(self, db: Session, *, now: datetime | None = None) -> int:
        cutoff = now or _now()
        result = db.execute(delete(SessionMemory).where(SessionMemory.expires_at <= cutoff))
        db.commit()
        return int(result.rowcount or 0)

    def _latest(self, db: Session, principal: AuthPrincipal, request: Request, session_id: str) -> SessionMemory | None:
        row = db.scalar(
            select(SessionMemory)
            .where(SessionMemory.session_id == session_id)
            .order_by(SessionMemory.updated_at.desc())
        )
        if row is not None:
            _access(principal, row, request)
        return row

    def _context(self, row: SessionMemory) -> MemoryContext:
        return MemoryContext(
            session_id=row.session_id,
            summary=row.summary or "",
            messages=[MemoryMessage.model_validate(item) for item in row.messages or []],
            evidence=row.evidence or [],
            tool_results=row.tool_results or [],
            confirmations=row.confirmations or [],
            version=row.version,
            expires_at=row.expires_at,
        )

    def _bounded(self, current: list | None, incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return redact((list(current or []) + [redact(item) for item in incoming])[-self.max_items :])

    @staticmethod
    def _roll_summary(existing: str, messages: list[dict[str, Any]]) -> str:
        additions = " ".join(f"{item.get('role', 'unknown')}: {item.get('content', '')}" for item in messages)
        combined = f"{existing} {additions}".strip()
        return redact_text(combined)[-4000:]
