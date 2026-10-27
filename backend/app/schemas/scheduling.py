"""Contracts for deterministic SLA, inspection and dispatch planning."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Priority = Literal["P1", "P2", "P3", "P4"]


class SlaPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_type: str = Field(min_length=1, max_length=64)
    priority: Priority = "P3"
    region: str = Field(min_length=1, max_length=100)
    reported_at: datetime
    facility_criticality: str | None = Field(default=None, max_length=32)
    public_safety: bool = False
    repeated_report: bool = False
    current_status: str | None = Field(default=None, max_length=32)


class SlaPlanResult(BaseModel):
    priority: Priority
    first_response_due_at: datetime
    resolution_due_at: datetime
    sla_minutes: int = Field(gt=0)
    escalation_reasons: list[str] = Field(default_factory=list, max_length=12)
    explanation: str


class InspectionPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    facility_id: str | None = Field(default=None, max_length=64)
    region: str = Field(min_length=1, max_length=100)
    priority: Priority = "P3"
    due_at: datetime | None = None
    requested_at: datetime | None = None
    duration_minutes: int = Field(default=60, ge=15, le=480)
    public_safety: bool = False


class InspectionPlanResult(BaseModel):
    priority: Priority
    scheduled_at: datetime
    due_at: datetime
    candidate_assignee_ids: list[str] = Field(default_factory=list, max_length=20)
    recommendation: str
    requires_confirmation: bool = False
    confirmation_reasons: list[str] = Field(default_factory=list, max_length=8)


class DispatchPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_order_id: str | None = Field(default=None, max_length=64)
    region: str = Field(min_length=1, max_length=100)
    priority: Priority = "P3"
    issue_type: str = Field(min_length=1, max_length=64)
    scheduled_for: datetime
    duration_minutes: int = Field(default=120, ge=15, le=720)
    required_skill: str | None = Field(default=None, max_length=64)
    preferred_assignee_id: str | None = Field(default=None, max_length=64)
    capacity_limit: int = Field(default=3, ge=1, le=20)
    public_safety: bool = False
    repeated_assignment: bool = False


class DispatchCandidate(BaseModel):
    assignee_id: str
    name: str
    region: str | None
    available: bool
    conflict_reasons: list[str] = Field(default_factory=list, max_length=8)
    score: float = Field(ge=0, le=1)


class DispatchPlanResult(BaseModel):
    candidates: list[DispatchCandidate] = Field(default_factory=list, max_length=50)
    selected_assignee_id: str | None = None
    requires_confirmation: bool
    confirmation_reasons: list[str] = Field(default_factory=list, max_length=12)
    blocked_reasons: list[str] = Field(default_factory=list, max_length=12)
    alternate_plan: str | None = None
    explanation: str
