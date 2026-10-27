"""Structured contracts for safety and repair acceptance recommendations."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SafetyAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    facility_type: str = Field(min_length=1, max_length=64)
    issue_type: str = Field(min_length=1, max_length=64)
    work_description: str = Field(min_length=1, max_length=3000)
    region: str = Field(min_length=1, max_length=100)
    site_conditions: list[str] = Field(default_factory=list, max_length=20)
    proposed_action: str | None = Field(default=None, max_length=2000)
    live_power: bool = False
    gas_risk: bool = False
    high_work: bool = False
    road_closure: bool = False


class SafetyAssessmentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    risk_labels: list[str] = Field(default_factory=list, max_length=12)
    isolation_measures: list[str] = Field(default_factory=list, max_length=12)
    ppe: list[str] = Field(default_factory=list, max_length=12)
    barriers: list[str] = Field(default_factory=list, max_length=12)
    traffic_controls: list[str] = Field(default_factory=list, max_length=12)
    prohibited_actions: list[str] = Field(default_factory=list, max_length=12)
    requires_confirmation: bool
    confirmation_reasons: list[str] = Field(default_factory=list, max_length=12)
    safe_to_proceed: bool = False
    rationale: list[str] = Field(default_factory=list, max_length=12)


class AcceptanceAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_order_id: str = Field(min_length=1, max_length=64)
    work_order_status: str = Field(min_length=1, max_length=32)
    handling_notes: str | None = Field(default=None, max_length=10000)
    evidence_uris: list[str] = Field(default_factory=list, max_length=20)
    required_checks: list[str] = Field(default_factory=list, max_length=20)
    completed_checks: list[str] = Field(default_factory=list, max_length=20)
    observed_defects: list[str] = Field(default_factory=list, max_length=20)
    public_safety: bool = False


class AcceptanceAssessmentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["ACCEPTED", "REWORK_REQUIRED", "CONDITIONAL_ACCEPTANCE"]
    work_order_id: str
    missing_evidence: list[str] = Field(default_factory=list, max_length=20)
    defects: list[str] = Field(default_factory=list, max_length=20)
    recommended_actions: list[str] = Field(default_factory=list, max_length=20)
    requires_confirmation: bool
    rationale: list[str] = Field(default_factory=list, max_length=12)
    evidence: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
