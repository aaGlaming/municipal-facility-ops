"""Security and business audit event recording."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import Request

_SENSITIVE_KEYS = {"password", "passwd", "token", "secret", "api_key", "authorization", "cookie"}


def _redact(value: Any, key: str = "") -> Any:
    if key.casefold() in _SENSITIVE_KEYS or any(
        part in key.casefold() for part in ("password", "token", "secret", "api_key")
    ):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(item_key): _redact(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_redact(item, key) for item in value[:50]]
    if isinstance(value, str):
        return value[:8000]
    return value


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
        "details": _redact(details or {}),
    }
    path = Path(os.getenv("LOG_DIRECTORY", "logs")) / "security" / "security_events.jsonl"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
    except OSError:
        # Authentication must remain available if local audit storage is temporarily unavailable.
        return
