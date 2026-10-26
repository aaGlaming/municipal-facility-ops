"""Security and business audit event recording."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import Request


def record_security_event(
    event_type: str,
    request: Request | None = None,
    subject: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Append a redacted security event to a local JSONL audit stream."""
    payload = {
        "event_type": event_type,
        "occurred_at": datetime.now(UTC).isoformat(),
        "subject": subject,
        "request_id": getattr(getattr(request, "state", None), "request_id", "") if request else "",
        "trace_id": getattr(getattr(request, "state", None), "trace_id", "") if request else "",
        "details": {
            key: value for key, value in (details or {}).items() if key.lower() not in {"password", "token", "secret"}
        },
    }
    path = Path("logs/security_events.jsonl")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    except OSError:
        # Authentication must remain available if local audit storage is temporarily unavailable.
        return
