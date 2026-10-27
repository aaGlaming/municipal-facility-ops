from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Priority = Literal["P1", "P2", "P3", "P4"]


class WorkOrderCreate(BaseModel):
    report_id: str | None = Field(default=None, max_length=64)
    facility_id: str | None = Field(default=None, max_length=64)
    priority: Priority = "P3"
    problem_type: str | None = Field(default=None, max_length=64)
    assignee_id: str | None = Field(default=None, max_length=64)
    vendor_id: str | None = Field(default=None, max_length=64)
    due_at: datetime | None = None
    idempotency_key: str = Field(min_length=1, max_length=255)
    region: str | None = Field(default=None, max_length=100)


class WorkOrderStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=32)
    idempotency_key: str = Field(min_length=1, max_length=255)
    assignee_id: str | None = Field(default=None, max_length=64)
    vendor_id: str | None = Field(default=None, max_length=64)
    handling_notes: str | None = Field(default=None, max_length=10000)
    evidence_uri: str | None = Field(default=None, max_length=1024)
    human_confirmation: bool = False


class AcceptanceCreate(BaseModel):
    result: Literal["ACCEPTED", "REJECTED"]
    reason: str | None = Field(default=None, max_length=10000)
    evidence_uri: str | None = Field(default=None, max_length=1024)


class InspectionCreate(BaseModel):
    facility_id: str | None = Field(default=None, max_length=64)
    area: str | None = Field(default=None, max_length=128)
    priority: Priority = "P3"
    scheduled_at: datetime | None = None
    due_at: datetime | None = None
    region: str | None = Field(default=None, max_length=100)


class InspectionAssign(BaseModel):
    assignee_id: str = Field(min_length=1, max_length=64)


class InspectionStatusUpdate(BaseModel):
    status: Literal["SCHEDULED", "ASSIGNED", "IN_PROGRESS", "DEFERRED", "COMPLETED"]
    reason: str | None = Field(default=None, max_length=10000)
    result_notes: str | None = Field(default=None, max_length=10000)
