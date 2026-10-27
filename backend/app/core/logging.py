import json
import logging
import time
from collections.abc import Mapping
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Lock
from typing import Any

from app.memory.store import redact


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in (
            "request_id",
            "trace_id",
            "agent_run_id",
            "tool_call_id",
            "user_id",
            "status_code",
            "duration_ms",
            "input_tokens",
            "output_tokens",
            "cost_usd",
            "retry_count",
            "error_code",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = redact(value, key=field)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(redact(payload), ensure_ascii=False, default=str)


class ModuleRoutingHandler(logging.Handler):
    """Route structured records into one rotating JSONL file per application module."""

    def __init__(self, directory: str | Path, max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5) -> None:
        super().__init__()
        self.directory = Path(directory)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self._handlers: dict[str, RotatingFileHandler] = {}
        self._lock = Lock()

    @staticmethod
    def module_name(logger_name: str) -> str:
        parts = logger_name.split(".")
        if parts and parts[0] == "app" and len(parts) > 1:
            return parts[1].replace("-", "_")
        return "backend"

    def _handler_for(self, module: str) -> RotatingFileHandler:
        with self._lock:
            handler = self._handlers.get(module)
            if handler is None:
                module_directory = self.directory / module
                module_directory.mkdir(parents=True, exist_ok=True)
                handler = RotatingFileHandler(
                    module_directory / f"{module}.jsonl",
                    maxBytes=self.max_bytes,
                    backupCount=self.backup_count,
                    encoding="utf-8",
                )
                handler.setFormatter(JsonFormatter())
                self._handlers[module] = handler
            return handler

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._handler_for(self.module_name(record.name)).emit(record)
        except OSError:
            # Console logging must remain available if the local log directory is unavailable.
            return

    def close(self) -> None:
        with self._lock:
            for handler in self._handlers.values():
                handler.close()
            self._handlers.clear()
        super().close()


def configure_logging(level: str = "INFO", log_directory: str = "logs") -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())
    if not any(
        isinstance(handler, logging.StreamHandler) and not isinstance(handler, ModuleRoutingHandler)
        for handler in root.handlers
    ):
        stream_handler: logging.Handler = logging.StreamHandler()
        stream_handler.setFormatter(JsonFormatter())
        root.addHandler(stream_handler)
    if not any(isinstance(handler, ModuleRoutingHandler) for handler in root.handlers):
        root.addHandler(ModuleRoutingHandler(log_directory))


def request_log_fields(request: Any, status_code: int, started_at: float) -> Mapping[str, Any]:
    return {
        "request_id": getattr(request.state, "request_id", ""),
        "trace_id": getattr(request.state, "trace_id", ""),
        "user_id": getattr(request.state, "user_id", ""),
        "status_code": status_code,
        "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
    }
