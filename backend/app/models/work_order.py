from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InspectionTask(Base):
    __tablename__ = "inspection_tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    facility_id: Mapped[str | None] = mapped_column(String(64), index=True)
    area: Mapped[str | None] = mapped_column(String(128))
    priority: Mapped[str | None] = mapped_column(String(16))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime)
    due_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    assignee_id: Mapped[str | None] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    region: Mapped[str | None] = mapped_column(String(100), index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    data_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    result_notes: Mapped[str | None] = mapped_column(Text)
    defer_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)


class WorkOrder(Base):
    __tablename__ = "work_orders"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_work_order_idempotency"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    report_id: Mapped[str | None] = mapped_column(String(64), index=True)
    facility_id: Mapped[str | None] = mapped_column(String(64), index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    problem_type: Mapped[str | None] = mapped_column(String(64))
    assignee_id: Mapped[str | None] = mapped_column(String(64), index=True)
    vendor_id: Mapped[str | None] = mapped_column(String(64), index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str | None] = mapped_column(String(100), index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    data_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)


class AcceptanceRecord(Base):
    __tablename__ = "acceptance_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    work_order_id: Mapped[str] = mapped_column(String(64), index=True)
    reviewer_id: Mapped[str | None] = mapped_column(String(64))
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    evidence_uri: Mapped[str | None] = mapped_column(String(1024))
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="internal")
    source_system: Mapped[str] = mapped_column(String(64), nullable=False, default="platform")
    data_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)


class WorkOrderStatusEvent(Base):
    __tablename__ = "work_order_status_events"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    work_order_id: Mapped[str] = mapped_column(String(64), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    from_status: Mapped[str] = mapped_column(String(32), nullable=False)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
