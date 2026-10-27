from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SessionMemory(Base):
    __tablename__ = "session_memories"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"MEM-{uuid4().hex[:16].upper()}")
    session_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    roles: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    region: Mapped[str | None] = mapped_column(String(100), index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    messages: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    tool_results: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    confirmations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
