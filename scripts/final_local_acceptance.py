"""Repeatable local HTTP acceptance probe for backend and frontend services."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _get(url: str) -> tuple[int, Any]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            body = response.read().decode("utf-8")
            try:
                return response.status, json.loads(body)
            except json.JSONDecodeError:
                return response.status, body
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        try:
            return error.code, json.loads(body)
        except json.JSONDecodeError:
            return error.code, body


def main() -> None:
    health_status, health = _get("http://127.0.0.1:8000/health")
    ready_status, ready = _get("http://127.0.0.1:8000/ready")
    frontend_status, frontend = _get("http://127.0.0.1:5173/login")
    result = {
        "checked_at": datetime.now(UTC).isoformat(),
        "backend_health": {
            "status_code": health_status,
            "passed": health_status == 200 and health.get("status") == "ok",
        },
        "backend_readiness": {"status_code": ready_status, "passed": ready_status == 200, "response": ready},
        "frontend_shell": {
            "status_code": frontend_status,
            "passed": frontend_status == 200 and '<div id="app"></div>' in frontend,
        },
        "dependency_gate": "passed" if ready_status == 200 else "blocked_by_local_dependencies",
        "notes": ["/ready 返回 503 时保留依赖 checks，待 Step36 Compose 启动 MySQL、Chroma 和模型服务后复验。"],
    }
    output = ROOT / "evaluation/reports/step33-local-acceptance.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
