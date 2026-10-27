from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Technician(Base):
    __tablename__ = "technicians"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    region: Mapped[str | None] = mapped_column(String(100), index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str | None] = mapped_column(String(100), index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
