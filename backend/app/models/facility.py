from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    district: Mapped[str | None] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(100), index=True)
    longitude: Mapped[Decimal | float | None] = mapped_column(Numeric(10, 7))
    latitude: Mapped[Decimal | float | None] = mapped_column(Numeric(10, 7))
    external_id: Mapped[str | None] = mapped_column(String(128))
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    data_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)


class Facility(Base):
    __tablename__ = "facilities"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    facility_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    criticality: Mapped[str | None] = mapped_column(String(32))
    location_id: Mapped[int | None] = mapped_column(Integer, index=True)
    region: Mapped[str | None] = mapped_column(String(100), index=True)
    external_id: Mapped[str | None] = mapped_column(String(128))
    install_date: Mapped[date | None] = mapped_column(Date)
    condition_score: Mapped[int | None] = mapped_column(Integer)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    data_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)


class CitizenReport(Base):
    __tablename__ = "citizen_reports"
    __table_args__ = (UniqueConstraint("source_system", "external_id", name="uq_report_source_external"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    facility_id: Mapped[str | None] = mapped_column(String(64), index=True)
    reporter_user_id: Mapped[str | None] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), index=True)
    subcategory: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="NEW", index=True)
    priority: Mapped[str | None] = mapped_column(String(16))
    external_id: Mapped[str | None] = mapped_column(String(128))
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    data_version: Mapped[str] = mapped_column(String(64), nullable=False, default="v1")
    region: Mapped[str | None] = mapped_column(String(100), index=True)
    latitude: Mapped[Decimal | float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | float | None] = mapped_column(Numeric(10, 7))
    idempotency_key: Mapped[str | None] = mapped_column(String(255), unique=True)
    reported_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
