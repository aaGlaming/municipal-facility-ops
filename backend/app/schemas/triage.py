"""Structured contracts for issue triage and facility identification."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class TriageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, max_length=5000)
    category_hint: str | None = Field(default=None, max_length=64)
    subcategory_hint: str | None = Field(default=None, max_length=128)
    address: str | None = Field(default=None, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    region: str = Field(min_length=1, max_length=100)
    reported_at: str | None = Field(default=None, max_length=64)


class FacilityCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    facility_id: str
    facility_code: str
    facility_type: str
    name: str
    region: str | None
    confidence: float = Field(ge=0, le=1)
    match_reasons: list[str] = Field(default_factory=list, max_length=8)


class DuplicateReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str
    facility_id: str | None
    description: str
    status: str
    similarity: float = Field(ge=0, le=1)


class TriageResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    priority: Literal["P1", "P2", "P3", "P4"]
    confidence: float = Field(ge=0, le=1)
    candidates: list[FacilityCandidate] = Field(default_factory=list, max_length=10)
    selected_facility_id: str | None = None
    requires_confirmation: bool
    missing_fields: list[str] = Field(default_factory=list, max_length=16)
    duplicate_reports: list[DuplicateReport] = Field(default_factory=list, max_length=10)
    rationale: list[str] = Field(default_factory=list, max_length=12)
    evidence: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
