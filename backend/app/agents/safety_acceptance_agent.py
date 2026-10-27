"""Safety controls and repair acceptance recommendation Agents."""

from __future__ import annotations

from fastapi import Request

from app.core.auth import AuthPrincipal, ensure_region_access
from app.schemas.safety_acceptance import (
    AcceptanceAssessmentRequest,
    AcceptanceAssessmentResult,
    SafetyAssessmentRequest,
    SafetyAssessmentResult,
)

SAFETY_PROMPT = """你是市政维修安全 Agent。识别带电、高空、燃气、封路、挖掘和危险区域风险，生成隔离、PPE、围挡和交通防护清单。
涉及现场动作只能生成建议，不能自动批准；任何高风险场景必须人工确认后才能继续。"""
ACCEPTANCE_PROMPT = """你是维修验收 Agent。根据工单完成状态、处理说明、验收清单、维修证据和缺陷判断通过、条件通过或返工。
证据不足、工单未完成或存在缺陷时不得建议直接关闭；最终验收和返工状态必须由权限允许的人员通过受控工具提交。"""


class SafetyAgent:
    def assess(self, payload: SafetyAssessmentRequest) -> SafetyAssessmentResult:
        text = " ".join(
            [payload.facility_type, payload.issue_type, payload.work_description, *payload.site_conditions]
        ).casefold()
        labels: list[str] = []
        isolation: list[str] = []
        ppe: list[str] = ["安全帽", "反光背心", "防滑安全鞋", "防护手套"]
        barriers: list[str] = ["设置作业区边界和警示牌", "维修完成前不得拆除临时防护"]
        traffic: list[str] = []
        prohibited: list[str] = ["未确认现场条件前不得开始维修", "不得绕过许可、隔离和验收流程"]
        confirmation: list[str] = []
        if payload.live_power or any(word in text for word in ("带电", "漏电", "live power", "energized")):
            labels.append("LIVE_POWER")
            isolation.extend(["断电并执行挂牌上锁", "使用验电器确认无电后再作业"])
            ppe.extend(["绝缘手套", "绝缘工具"])
            confirmation.append("带电风险必须由授权人员确认隔离")
        if payload.gas_risk or any(word in text for word in ("燃气", "天然气", "gas")):
            labels.append("GAS")
            isolation.extend(["关闭并隔离气源", "检测可燃气体浓度并保持通风"])
            ppe.append("防静电 PPE")
            confirmation.append("燃气风险必须完成气体检测和人工确认")
        if payload.high_work or any(word in text for word in ("高空", "梯", "高处", "height")):
            labels.append("HIGH_WORK")
            isolation.append("检查高处作业许可和安全锚点")
            ppe.extend(["安全带", "防坠落装置"])
            confirmation.append("高处作业必须确认防坠落措施")
        if payload.road_closure or any(word in text for word in ("封路", "车道", "交通", "road closure")):
            labels.append("TRAFFIC")
            traffic.extend(["设置交通导流和缓冲区", "安排现场交通防护人员"])
            barriers.append("设置车辆和行人隔离围挡")
            confirmation.append("封路或交通影响必须经现场负责人确认")
        if any(word in text for word in ("挖掘", "开挖", "深坑", "excavat")):
            labels.append("EXCAVATION")
            isolation.append("确认地下管线和开挖许可")
            barriers.append("设置坑槽围挡和夜间警示灯")
            confirmation.append("开挖作业必须完成管线确认")
        if not labels:
            rationale = ["未识别到需要升级的高风险标签", "仍需按通用 PPE、边界和许可要求作业"]
            return SafetyAssessmentResult(
                risk_level="LOW",
                risk_labels=[],
                isolation_measures=isolation,
                ppe=sorted(set(ppe)),
                barriers=barriers,
                traffic_controls=traffic,
                prohibited_actions=prohibited,
                requires_confirmation=False,
                confirmation_reasons=[],
                safe_to_proceed=True,
                rationale=rationale,
            )
        risk_level = (
            "CRITICAL" if len(labels) >= 2 and any(label in labels for label in ("LIVE_POWER", "GAS")) else "HIGH"
        )
        return SafetyAssessmentResult(
            risk_level=risk_level,
            risk_labels=labels,
            isolation_measures=list(dict.fromkeys(isolation)),
            ppe=list(dict.fromkeys(ppe)),
            barriers=list(dict.fromkeys(barriers)),
            traffic_controls=traffic,
            prohibited_actions=prohibited,
            requires_confirmation=True,
            confirmation_reasons=confirmation,
            safe_to_proceed=False,
            rationale=["识别到高风险作业条件", "清单仅用于现场复核，不代表自动批准"],
        )


class AcceptanceAgent:
    def evaluate(self, payload: AcceptanceAssessmentRequest) -> AcceptanceAssessmentResult:
        missing: list[str] = []
        defects = list(payload.observed_defects)
        actions: list[str] = []
        rationale: list[str] = []
        if payload.work_order_status != "COMPLETED":
            missing.append("工单必须处于 COMPLETED 状态")
        if not payload.handling_notes or not payload.handling_notes.strip():
            missing.append("处理说明")
        if not payload.evidence_uris:
            missing.append("维修证据 URI")
        missing_checks = [check for check in payload.required_checks if check not in payload.completed_checks]
        if missing_checks:
            missing.extend([f"验收检查项：{check}" for check in missing_checks])
        if defects:
            actions.extend([f"修复缺陷：{defect}" for defect in defects])
        if missing or defects:
            decision = (
                "REWORK_REQUIRED" if defects or payload.work_order_status != "COMPLETED" else "CONDITIONAL_ACCEPTANCE"
            )
            rationale.append("验收条件未全部满足，不能直接关闭工单")
            if missing:
                actions.append("补齐缺失的处理说明、检查项和维修证据")
        else:
            decision = "ACCEPTED"
            rationale.append("工单已完成，处理说明、证据和必需检查项齐全")
        if payload.public_safety:
            rationale.append("公共安全工单仍需授权验收人员人工确认")
        return AcceptanceAssessmentResult(
            decision=decision,
            work_order_id=payload.work_order_id,
            missing_evidence=missing,
            defects=defects,
            recommended_actions=actions,
            requires_confirmation=True,
            rationale=rationale,
            evidence=[
                {
                    "source_type": "work_order",
                    "work_order_id": payload.work_order_id,
                    "evidence_count": len(payload.evidence_uris),
                }
            ],
        )


def assess_safety(
    principal: AuthPrincipal, request: Request, payload: SafetyAssessmentRequest
) -> SafetyAssessmentResult:
    ensure_region_access(principal, payload.region, request)
    return SafetyAgent().assess(payload)


def evaluate_acceptance(payload: AcceptanceAssessmentRequest) -> AcceptanceAssessmentResult:
    return AcceptanceAgent().evaluate(payload)
