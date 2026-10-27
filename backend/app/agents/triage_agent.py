"""Problem triage and facility identification Agent."""

from __future__ import annotations

import difflib
import re
from datetime import UTC, datetime, timedelta

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import AuthPrincipal, ensure_region_access
from app.models.facility import CitizenReport, Facility, Location
from app.schemas.triage import DuplicateReport, FacilityCandidate, TriageRequest, TriageResult

TRIAGE_PROMPT = """你是市政设施问题分诊 Agent。只根据用户描述、设施台账和可追溯历史证据输出结构化分诊结果。
先判断问题类别和优先级，再匹配设施候选。置信度低于阈值时必须请求人工确认，不得直接绑定 facility_id。
禁止创建或修改设施台账；所有候选必须保留 facility_id、匹配理由和来源证据。"""
LOW_CONFIDENCE_THRESHOLD = 0.75

_CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("road_damage", ("坑洼", "坑洞", "坑", "路面", "裂缝", "pothole", "road")),
    ("street_light", ("路灯", "灯杆", "照明", "street light", "lamp")),
    ("traffic_signal", ("信号灯", "红绿灯", "交通灯", "traffic signal")),
    ("drainage", ("积水", "排水", "井盖", "下水道", "drain")),
    ("waste_bin", ("垃圾桶", "垃圾", "废物", "waste", "bin")),
    ("sidewalk", ("人行道", "盲道", " sidewalk", "sidewalk")),
)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _classify(request: TriageRequest) -> tuple[str, float, list[str]]:
    text = _normalize(request.description)
    if request.category_hint:
        return request.category_hint, 0.9, ["用户提供了问题类别"]
    for category, keywords in _CATEGORY_RULES:
        matched = [keyword.strip() for keyword in keywords if keyword.strip() in text]
        if matched:
            return category, min(0.96, 0.72 + 0.08 * len(matched)), [f"描述命中关键词：{', '.join(matched)}"]
    return "other", 0.4, ["未命中已配置的问题类别规则"]


def classify_issue(payload: TriageRequest) -> tuple[str, float, str]:
    """Return deterministic category, confidence and priority for offline evaluation."""

    category, confidence, _ = _classify(payload)
    return category, confidence, _priority(payload, category)


def _priority(request: TriageRequest, category: str) -> str:
    text = _normalize(request.description)
    if any(word in text for word in ("危险", "事故", "伤人", "漏电", "紧急", "blocked", "danger")):
        return "P1"
    if category in {"traffic_signal", "drainage"}:
        return "P2"
    if any(word in text for word in ("影响通行", "严重", "large", "major")):
        return "P2"
    if category == "other":
        return "P4"
    return "P3"


def _candidate_score(
    facility: Facility, location: Location | None, request: TriageRequest, category: str
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    if facility.type == category:
        score += 0.62
        reasons.append("设施类型与问题类别一致")
    text = _normalize(request.description + " " + (request.address or ""))
    searchable = _normalize(f"{facility.name} {facility.facility_code} {location.address if location else ''}")
    tokens = [token for token in re.split(r"[^\w\u4e00-\u9fff]+", text) if len(token) >= 2]
    overlap = [token for token in tokens if token in searchable]
    if overlap:
        score += min(0.28, 0.08 * len(overlap))
        reasons.append(f"地址或名称命中：{', '.join(overlap[:3])}")
    if (
        request.latitude is not None
        and request.longitude is not None
        and location
        and location.latitude is not None
        and location.longitude is not None
    ):
        distance_hint = abs(float(location.latitude) - request.latitude) + abs(
            float(location.longitude) - request.longitude
        )
        if distance_hint < 0.001:
            score += 0.25
            reasons.append("坐标接近")
        elif distance_hint < 0.01:
            score += 0.1
            reasons.append("坐标位于附近")
    return min(score, 0.99), reasons


def _duplicates(db: Session, request: TriageRequest, category: str) -> list[DuplicateReport]:
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=24)
    stmt = (
        select(CitizenReport)
        .where(
            CitizenReport.region == request.region,
            CitizenReport.category == category,
            CitizenReport.reported_at >= cutoff,
            CitizenReport.is_deleted.is_(False),
        )
        .order_by(CitizenReport.reported_at.desc())
        .limit(50)
    )
    result: list[DuplicateReport] = []
    normalized = _normalize(request.description)
    for report in db.scalars(stmt).all():
        similarity = difflib.SequenceMatcher(None, normalized, _normalize(report.description)).ratio()
        if similarity >= 0.72:
            result.append(
                DuplicateReport(
                    report_id=report.id,
                    facility_id=report.facility_id,
                    description=report.description,
                    status=report.status,
                    similarity=round(similarity, 3),
                )
            )
    return result[:10]


class TriageAgent:
    """Read-only triage and facility matching; writes no facility records."""

    def __init__(self, confidence_threshold: float = LOW_CONFIDENCE_THRESHOLD) -> None:
        if not 0 < confidence_threshold <= 1:
            raise ValueError("confidence_threshold must be in (0, 1]")
        self.confidence_threshold = confidence_threshold

    def run(self, db: Session, principal: AuthPrincipal, request: Request, payload: TriageRequest) -> TriageResult:
        ensure_region_access(principal, payload.region, request)
        category, category_confidence, rationale = _classify(payload)
        priority = _priority(payload, category)
        rows = db.execute(
            select(Facility, Location)
            .outerjoin(Location, Facility.location_id == Location.id)
            .where(Facility.region == payload.region, Facility.is_deleted.is_(False))
            .limit(200)
        ).all()
        candidates: list[FacilityCandidate] = []
        for facility, location in rows:
            score, reasons = _candidate_score(facility, location, payload, category)
            if score > 0:
                candidates.append(
                    FacilityCandidate(
                        facility_id=facility.id,
                        facility_code=facility.facility_code,
                        facility_type=facility.type,
                        name=facility.name,
                        region=facility.region,
                        confidence=round(score, 3),
                        match_reasons=reasons,
                    )
                )
        candidates.sort(key=lambda item: (-item.confidence, item.facility_id))
        candidates = candidates[:10]
        best = candidates[0] if candidates else None
        confidence = round(min(category_confidence, best.confidence if best else category_confidence), 3)
        missing_fields: list[str] = []
        if not payload.address and payload.latitude is None:
            missing_fields.append("address_or_coordinates")
        if not candidates:
            missing_fields.append("facility_identifier")
        requires_confirmation = confidence < self.confidence_threshold or best is None
        selected = best.facility_id if best and not requires_confirmation else None
        duplicates = _duplicates(db, payload, category)
        if duplicates:
            rationale.append("发现 24 小时内相似报修，需先核对是否重复")
        if requires_confirmation:
            rationale.append(f"设施匹配置信度 {confidence:.3f} 低于确认阈值 {self.confidence_threshold:.3f}")
        else:
            rationale.append("设施候选达到自动关联阈值")
        return TriageResult(
            category=category,
            priority=priority,
            confidence=confidence,
            candidates=candidates,
            selected_facility_id=selected,
            requires_confirmation=requires_confirmation,
            missing_fields=missing_fields,
            duplicate_reports=duplicates,
            rationale=rationale,
            evidence=[
                {"source_type": "facility_registry", "region": payload.region, "candidate_count": len(candidates)}
            ],
        )


def run_triage(
    db: Session,
    principal: AuthPrincipal,
    request: Request,
    payload: TriageRequest,
    confidence_threshold: float = LOW_CONFIDENCE_THRESHOLD,
) -> TriageResult:
    return TriageAgent(confidence_threshold).run(db, principal, request, payload)
