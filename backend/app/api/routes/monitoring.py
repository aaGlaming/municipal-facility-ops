"""Operational monitoring and audit read APIs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.routes.health import check_dependencies
from app.core.auth import AuthPrincipal, require_permission
from app.core.config import Settings, get_settings
from app.core.dependencies import get_db_session
from app.core.monitoring import metrics
from app.models.agent_run import AgentRun

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/overview")
def overview(request: Request, principal: AuthPrincipal = Depends(require_permission("agent:read"))) -> dict[str, Any]:
    settings: Settings = getattr(request.app.state, "settings", None) or get_settings()
    return {
        "status": "ok",
        "trace_id": request.state.trace_id,
        "metrics": metrics.snapshot(check_dependencies(settings)),
    }


@router.get("/runs")
def runs(
    status: str | None = Query(default=None, max_length=32),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db_session),
    principal: AuthPrincipal = Depends(require_permission("agent:read")),
) -> dict[str, Any]:
    statement = select(AgentRun)
    if status:
        statement = statement.where(AgentRun.status == status)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(
        statement.order_by(AgentRun.started_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    items = []
    for row in rows:
        duration_ms = None
        if row.finished_at is not None:
            duration_ms = round((row.finished_at - row.started_at).total_seconds() * 1000, 2)
        items.append(
            {
                "id": row.id,
                "agent_name": row.agent_name,
                "trace_id": row.trace_id,
                "user_id": row.user_id,
                "region": row.region,
                "status": row.status,
                "iterations": row.iterations,
                "input_tokens": row.input_tokens,
                "output_tokens": row.output_tokens,
                "stop_reason": row.stop_reason,
                "started_at": row.started_at,
                "finished_at": row.finished_at,
                "duration_ms": duration_ms,
            }
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/audit")
def audit(
    event_type: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=100, ge=1, le=500),
    principal: AuthPrincipal = Depends(require_permission("audit:read")),
) -> dict[str, Any]:
    path = Path(get_settings().log_directory) / "security" / "security_events.jsonl"
    items: list[dict[str, Any]] = []
    if path.exists():
        for line in reversed(path.read_text(encoding="utf-8").splitlines()):
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event_type and item.get("event_type") != event_type:
                continue
            items.append(item)
            if len(items) >= limit:
                break
    return {"items": items, "count": len(items)}


@router.post("/alerts/{alert_id}/close")
def close_alert(alert_id: str, principal: AuthPrincipal = Depends(require_permission("audit:write"))) -> dict[str, Any]:
    alert = metrics.close_alert(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail={"code": "ALERT_NOT_FOUND", "message": "告警不存在或已清理"})
    return alert
