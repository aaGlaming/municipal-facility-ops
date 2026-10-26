import json
import logging
import time
from collections.abc import Mapping
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("request_id", "trace_id", "agent_run_id", "tool_call_id", "status_code", "duration_ms"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())
    if not root.handlers:
        handler: logging.Handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)
    else:
        for handler in root.handlers:
            handler.setFormatter(JsonFormatter())


def request_log_fields(request: Any, status_code: int, started_at: float) -> Mapping[str, Any]:
    return {
        "request_id": getattr(request.state, "request_id", ""),
        "trace_id": getattr(request.state, "trace_id", ""),
        "status_code": status_code,
        "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
    }
