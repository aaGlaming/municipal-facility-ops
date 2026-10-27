from app.agents.acceptance_agent import AcceptanceAgent
from app.agents.safety_agent import SafetyAgent
from app.schemas.safety_acceptance import AcceptanceAssessmentRequest, SafetyAssessmentRequest


def test_live_power_and_traffic_are_blocked_for_confirmation() -> None:
    result = SafetyAgent().assess(
        SafetyAssessmentRequest(
            facility_type="traffic_signal",
            issue_type="electrical",
            work_description="带电信号灯维修并封路",
            region="中心区",
            live_power=True,
            road_closure=True,
        )
    )
    assert result.risk_level == "CRITICAL"
    assert "LIVE_POWER" in result.risk_labels
    assert "TRAFFIC" in result.risk_labels
    assert result.requires_confirmation is True
    assert result.safe_to_proceed is False
    assert result.traffic_controls
    assert result.isolation_measures


def test_low_risk_safety_checklist_can_proceed_with_controls() -> None:
    result = SafetyAgent().assess(
        SafetyAssessmentRequest(
            facility_type="waste_bin", issue_type="cleaning", work_description="清理垃圾桶", region="中心区"
        )
    )
    assert result.risk_level == "LOW"
    assert result.requires_confirmation is False
    assert result.safe_to_proceed is True
    assert result.ppe
    assert result.barriers


def test_acceptance_returns_accepted_only_when_evidence_and_checks_are_complete() -> None:
    result = AcceptanceAgent().evaluate(
        AcceptanceAssessmentRequest(
            work_order_id="WO-1",
            work_order_status="COMPLETED",
            handling_notes="已更换并测试",
            evidence_uris=["https://evidence/1"],
            required_checks=["功能测试", "现场清理"],
            completed_checks=["功能测试", "现场清理"],
        )
    )
    assert result.decision == "ACCEPTED"
    assert result.missing_evidence == []
    assert result.requires_confirmation is True


def test_acceptance_recommends_rework_for_defects_or_missing_evidence() -> None:
    result = AcceptanceAgent().evaluate(
        AcceptanceAssessmentRequest(
            work_order_id="WO-2",
            work_order_status="COMPLETED",
            handling_notes="修复完成",
            required_checks=["功能测试"],
            completed_checks=[],
            observed_defects=["仍有漏水"],
        )
    )
    assert result.decision == "REWORK_REQUIRED"
    assert result.defects == ["仍有漏水"]
    assert result.missing_evidence
    assert result.recommended_actions
