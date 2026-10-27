from datetime import UTC, datetime, timedelta

import pytest
from app.core.auth import AuthPrincipal
from app.db.base import Base
from app.memory.store import SessionMemoryStore
from app.models.session_memory import SessionMemory
from app.schemas.memory import MemoryAppend, MemoryMessage
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request


def _request() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/memory", "headers": []})


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _principal(user: str, roles: set[str] | None = None, regions: set[str] | None = None) -> AuthPrincipal:
    return AuthPrincipal(user, roles or {"dispatcher"}, {"agent:run"}, regions or {"中心区"})


def _message(content: str, role: str = "user") -> MemoryMessage:
    return MemoryMessage(role=role, content=content, created_at=datetime(2026, 1, 1))


def test_memory_is_redacted_bounded_and_restored() -> None:
    db = _db()
    store = SessionMemoryStore(ttl_seconds=3600, max_messages=2)
    principal = _principal("user-1")
    store.open(db, principal, _request(), "SESSION-1", region="中心区")
    for content in ["第一轮", "第二轮 token=secret-value", "第三轮 user@example.com", "第四轮"]:
        store.append(db, principal, _request(), "SESSION-1", MemoryAppend(message=_message(content)))
    context = store.load(db, principal, _request(), "SESSION-1")
    assert context is not None
    assert len(context.messages) == 2
    assert "第一轮" in context.summary
    assert "REDACTED" in context.summary or "[REDACTED_EMAIL]" in context.summary
    assert all("secret-value" not in message.content for message in context.messages)


def test_memory_user_role_and_region_isolation() -> None:
    db = _db()
    store = SessionMemoryStore()
    owner = _principal("owner", {"dispatcher"}, {"中心区"})
    store.open(db, owner, _request(), "SESSION-2", region="中心区")
    with pytest.raises(HTTPException) as user_error:
        store.load(db, _principal("other", {"dispatcher"}, {"中心区"}), _request(), "SESSION-2")
    assert user_error.value.status_code == 403
    with pytest.raises(HTTPException) as region_error:
        store.load(db, _principal("owner", {"dispatcher"}, {"南区"}), _request(), "SESSION-2")
    assert region_error.value.status_code == 403


def test_memory_expiry_delete_and_purge() -> None:
    db = _db()
    store = SessionMemoryStore(ttl_seconds=3600)
    principal = _principal("owner")
    store.open(db, principal, _request(), "SESSION-3", region="中心区")
    row = db.query(SessionMemory).filter_by(session_id="SESSION-3").one()
    row.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1)
    db.commit()
    assert store.load(db, principal, _request(), "SESSION-3") is None
    assert store.purge_expired(db) == 1
    store.open(db, principal, _request(), "SESSION-3", region="中心区")
    assert store.delete(db, principal, _request(), "SESSION-3") is True
    assert store.load(db, principal, _request(), "SESSION-3") is None
