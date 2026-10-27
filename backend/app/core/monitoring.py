"""Process-local request metrics and actionable dependency alerts."""

from __future__ import annotations

from collections import deque
from datetime import UTC, datetime
from threading import Lock
from typing import Any
from uuid import uuid4


class MetricsRegistry:
    def __init__(self, max_events: int = 2000) -> None:
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._alerts: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def record_request(self, *, status_code: int, duration_ms: float, path: str, method: str) -> None:
        with self._lock:
            self._events.append(
                {
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2),
                    "path": path,
                    "method": method,
                    "occurred_at": datetime.now(UTC).isoformat(),
                }
            )

    def snapshot(self, checks: dict[str, str]) -> dict[str, Any]:
        with self._lock:
            events = list(self._events)
            alerts = [dict(item) for item in self._alerts.values()]
        durations = sorted(float(item["duration_ms"]) for item in events)
        failures = sum(int(item["status_code"]) >= 500 for item in events)
        error_count = sum(int(item["status_code"]) >= 400 for item in events)
        error_rate = round(error_count / len(events), 4) if events else 0.0
        p95 = durations[min(len(durations) - 1, max(0, int(len(durations) * 0.95) - 1))] if durations else 0.0
        if failures and failures / max(1, len(events)) > 0.2:
            self._ensure_alert("HIGH_ERROR_RATE", "HTTP 5xx 错误率超过 20%", {"error_rate": error_rate})
        if p95 > 2000:
            self._ensure_alert("HIGH_LATENCY", "请求 P95 延迟超过 2 秒", {"p95_ms": p95})
        for dependency, status in checks.items():
            if status not in {"ok", "not_configured"}:
                self._ensure_alert(
                    f"DEPENDENCY_{dependency.upper()}_UNAVAILABLE",
                    f"{dependency} 依赖不可用",
                    {"dependency": dependency, "status": status},
                )
        with self._lock:
            alerts = [dict(item) for item in self._alerts.values()]
        return {
            "requests": len(events),
            "error_count": error_count,
            "server_error_count": failures,
            "error_rate": error_rate,
            "latency_ms": {"p50": self._percentile(durations, 0.50), "p95": round(p95, 2)},
            "dependencies": checks,
            "alerts": alerts,
            "active_alert_count": len([item for item in alerts if item.get("status") == "OPEN"]),
        }

    def close_alert(self, alert_id: str) -> dict[str, Any] | None:
        with self._lock:
            alert = self._alerts.get(alert_id)
            if alert is None:
                return None
            alert["status"] = "CLOSED"
            alert["closed_at"] = datetime.now(UTC).isoformat()
            return dict(alert)

    @staticmethod
    def _percentile(values: list[float], fraction: float) -> float:
        if not values:
            return 0.0
        index = min(len(values) - 1, max(0, int(len(values) * fraction) - 1))
        return round(values[index], 2)

    def _ensure_alert(self, code: str, message: str, details: dict[str, Any]) -> None:
        with self._lock:
            if any(item["code"] == code and item["status"] == "OPEN" for item in self._alerts.values()):
                return
            alert_id = f"ALT-{uuid4().hex[:16].upper()}"
            self._alerts[alert_id] = {
                "id": alert_id,
                "code": code,
                "message": message,
                "details": details,
                "status": "OPEN",
                "opened_at": datetime.now(UTC).isoformat(),
                "closed_at": None,
            }


metrics = MetricsRegistry()
