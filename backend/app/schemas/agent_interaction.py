from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentRunCreate(BaseModel):
    intent: str = Field(min_length=1, max_length=1000)
    description: str = Field(min_length=1, max_length=5000)
    session_id: str = Field(min_length=1, max_length=128)
    region: str | None = Field(default=None, max_length=100)
    agent_name: Literal["supervisor", "triage", "facility", "sla", "inspection", "dispatch", "safety", "acceptance"] = (
        "supervisor"
    )
    attachments: list[dict[str, Any]] = Field(default_factory=list, max_length=10)


class AgentDecisionAction(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str | None = Field(default=None, max_length=1000)


class AgentRunAction(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)
