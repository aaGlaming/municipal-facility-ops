from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class LocationResponse(BaseModel):
    address: str
    district: str | None
    region: str | None
    latitude: float | None
    longitude: float | None


class FacilityResponse(BaseModel):
    id: str
    facility_code: str
    type: str
    name: str
    status: str
    criticality: str | None
    region: str | None
    install_date: date | None
    condition_score: int | None
    source_type: str
    source_system: str
    location: LocationResponse | None = None
    distance_meters: float | None = None


class FacilityPage(BaseModel):
    items: list[FacilityResponse]
    total: int
    page: int
    page_size: int


class ReportCreate(BaseModel):
    description: str = Field(min_length=1, max_length=10000)
    category: str | None = Field(default=None, max_length=64)
    subcategory: str | None = Field(default=None, max_length=128)
    facility_id: str | None = Field(default=None, max_length=64)
    source: str = Field(default="web", min_length=1, max_length=64)
    external_id: str | None = Field(default=None, max_length=128)
    idempotency_key: str | None = Field(default=None, max_length=255)
    region: str | None = Field(default=None, max_length=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @field_validator("description")
    @classmethod
    def description_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("description must not be blank")
        return value


class PublicReportImportRequest(BaseModel):
    rows: list[ReportCreate] = Field(min_length=1, max_length=500)


class ReportStatusUpdate(BaseModel):
    status: Literal["NEW", "TRIAGED", "LINKED", "DUPLICATE", "REJECTED", "CLOSED"]


class ReportResponse(BaseModel):
    id: str
    facility_id: str | None
    source: str
    description: str
    category: str | None
    subcategory: str | None
    status: str
    priority: str | None
    external_id: str | None
    source_type: str
    source_system: str
    data_version: str
    region: str | None
    latitude: float | None
    longitude: float | None
    reported_at: datetime


class ReportPage(BaseModel):
    items: list[ReportResponse]
    total: int
    page: int
    page_size: int
