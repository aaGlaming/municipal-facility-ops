from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class MemoryMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "agent", "system", "human"]
    content: str = Field(min_length=1, max_length=8000)
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    summary: str = ""
    messages: list[MemoryMessage] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    confirmations: list[dict[str, Any]] = Field(default_factory=list)
    version: int = 1
    expires_at: datetime


class MemoryAppend(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: MemoryMessage | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    tool_results: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    confirmations: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
