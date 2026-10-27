"""SLA, inspection scheduling and work-order dispatch planning Agents."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import AuthPrincipal, ensure_region_access
from app.models.people import Technician
from app.models.work_order import InspectionTask, WorkOrder
from app.schemas.scheduling import (
    DispatchCandidate,
    DispatchPlanRequest,
    DispatchPlanResult,
    InspectionPlanRequest,
    InspectionPlanResult,
    SlaPlanRequest,
    SlaPlanResult,
)
from app.services.work_order_service import SLA_MINUTES

SLA_PROMPT = """你是市政运维 SLA 与调度 Agent。优先使用确定性 SLA 规则解释截止时间，再生成巡检和派工建议。
任何 P1、公共安全、重复派工、容量超限或人员时间冲突都必须拦截并请求人工确认。
不得通过外部 MCP 直接派工或改变工单状态；实际变更必须进入项目工具网关。"""
ACTIVE_WORK_ORDER_STATUSES = {
    "NEW",
    "TRIAGED",
    "ASSIGNED",
    "IN_PROGRESS",
    "WAITING_CONFIRMATION",
    "BLOCKED",
    "ESCALATED",
}


class SchedulingAgent:
    """Generate auditable plans. It does not mutate inspections or work orders."""

    def plan_sla(self, payload: SlaPlanRequest) -> SlaPlanResult:
        priority = payload.priority
        reasons: list[str] = []
        if payload.public_safety or payload.facility_criticality in {"critical", "high"}:
            if priority != "P1":
                reasons.append("公共安全或高关键性设施将优先级提升为 P1")
            priority = "P1"
        elif payload.repeated_report and priority in {"P3", "P4"}:
            priority = "P2"
            reasons.append("重复报修提升响应优先级")
        resolution_minutes = SLA_MINUTES[priority]
        first_response_minutes = max(30, min(120, resolution_minutes // 4))
        resolution_due = payload.reported_at + timedelta(minutes=resolution_minutes)
        first_due = payload.reported_at + timedelta(minutes=first_response_minutes)
        if payload.current_status in {"ESCALATED", "BLOCKED"}:
            reasons.append("当前工单处于升级或阻塞状态，需要调度员复核")
        return SlaPlanResult(
            priority=priority,
            first_response_due_at=first_due,
            resolution_due_at=resolution_due,
            sla_minutes=resolution_minutes,
            escalation_reasons=reasons,
            explanation=f"{priority} 优先级要求 {resolution_minutes} 分钟内完成处理，首次响应窗口为 {first_response_minutes} 分钟。",
        )

    def plan_inspection(
        self, db: Session, principal: AuthPrincipal, request: Request, payload: InspectionPlanRequest
    ) -> InspectionPlanResult:
        ensure_region_access(principal, payload.region, request)
        now = datetime.now(UTC).replace(tzinfo=None)
        requested = payload.requested_at or now
        interval = {"P1": 0, "P2": 4, "P3": 24, "P4": 72}[payload.priority]
        scheduled = requested + timedelta(hours=interval)
        due = payload.due_at or scheduled + timedelta(hours=max(2, payload.duration_minutes / 60 * 2))
        technicians = db.scalars(
            select(Technician).where(Technician.region == payload.region, Technician.active.is_(True)).limit(20)
        ).all()
        candidate_ids = [tech.id for tech in technicians]
        reasons: list[str] = []
        if payload.public_safety or payload.priority == "P1":
            reasons.append("P1 或公共安全巡检需要人工确认排班")
        return InspectionPlanResult(
            priority=payload.priority,
            scheduled_at=scheduled,
            due_at=due,
            candidate_assignee_ids=candidate_ids,
            recommendation=f"建议在 {scheduled.isoformat()} 前安排 {payload.region} 巡检。",
            requires_confirmation=bool(reasons),
            confirmation_reasons=reasons,
        )

    def plan_dispatch(
        self, db: Session, principal: AuthPrincipal, request: Request, payload: DispatchPlanRequest
    ) -> DispatchPlanResult:
        ensure_region_access(principal, payload.region, request)
        technicians = db.scalars(
            select(Technician).where(Technician.region == payload.region, Technician.active.is_(True)).limit(50)
        ).all()
        candidates: list[DispatchCandidate] = []
        window_start = payload.scheduled_for
        window_end = window_start + timedelta(minutes=payload.duration_minutes)
        for technician in technicians:
            conflict_reasons: list[str] = []
            active_orders = db.scalars(
                select(WorkOrder).where(
                    WorkOrder.assignee_id == technician.id,
                    WorkOrder.status.in_(ACTIVE_WORK_ORDER_STATUSES),
                    WorkOrder.region == payload.region,
                    WorkOrder.is_deleted.is_(False),
                )
            ).all()
            if len(active_orders) >= payload.capacity_limit:
                conflict_reasons.append("容量超限")
            if payload.work_order_id and any(order.id == payload.work_order_id for order in active_orders):
                conflict_reasons.append("重复派工")
            inspections = db.scalars(
                select(InspectionTask).where(
                    InspectionTask.assignee_id == technician.id,
                    InspectionTask.status.in_(("ASSIGNED", "IN_PROGRESS")),
                    InspectionTask.region == payload.region,
                )
            ).all()
            for inspection in inspections:
                if (
                    inspection.scheduled_at
                    and inspection.due_at
                    and inspection.scheduled_at < window_end
                    and inspection.due_at > window_start
                ):
                    conflict_reasons.append("巡检时间冲突")
                    break
            score = 1.0 if not conflict_reasons else max(0.0, 0.5 - 0.1 * len(conflict_reasons))
            if payload.preferred_assignee_id == technician.id:
                score = min(1.0, score + 0.1)
            candidates.append(
                DispatchCandidate(
                    assignee_id=technician.id,
                    name=technician.name,
                    region=technician.region,
                    available=not conflict_reasons,
                    conflict_reasons=conflict_reasons,
                    score=round(score, 3),
                )
            )
        candidates.sort(key=lambda item: (-item.available, -item.score, item.assignee_id))
        available = [item for item in candidates if item.available]
        confirmation_reasons: list[str] = []
        blocked: list[str] = []
        if payload.priority == "P1":
            confirmation_reasons.append("P1 工单派工需要人工确认")
        if payload.public_safety:
            confirmation_reasons.append("公共安全场景需要人工确认")
        if payload.repeated_assignment:
            confirmation_reasons.append("重复派工需要人工确认")
        if not available:
            blocked.append("没有满足区域、容量和时间冲突约束的人员")
            confirmation_reasons.append("无可用人员时需要调度员选择替代方案")
        selected = available[0].assignee_id if available and not confirmation_reasons else None
        alternate = "扩大时间窗口、降低非紧急任务优先级或转交区域供应商" if not available else None
        return DispatchPlanResult(
            candidates=candidates,
            selected_assignee_id=selected,
            requires_confirmation=bool(confirmation_reasons),
            confirmation_reasons=confirmation_reasons,
            blocked_reasons=blocked,
            alternate_plan=alternate,
            explanation="仅返回满足权限和容量约束的派工候选；实际派工须通过 work_order.assign 工具执行。",
        )


class SlaAgent(SchedulingAgent):
    """Compatibility name for SLA-only integrations."""


class DispatchAgent(SchedulingAgent):
    """Compatibility name for dispatch-only integrations."""


def plan_sla(payload: SlaPlanRequest) -> SlaPlanResult:
    return SchedulingAgent().plan_sla(payload)
