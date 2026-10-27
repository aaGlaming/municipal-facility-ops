"""Versioned Agent tool contracts, permissions and execution policy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.agent import AgentName

RiskLevel = Literal["READ_ONLY", "WRITE", "HIGH"]
ConfirmationPolicy = Literal["NEVER", "OPTIONAL", "REQUIRED"]


class FacilitySearchInput(BaseModel):
    facility_id: str | None = Field(default=None, max_length=64)
    query: str | None = Field(default=None, max_length=255)
    facility_type: str | None = Field(default=None, max_length=64)
    region: str | None = Field(default=None, max_length=100)
    page: int = Field(default=1, ge=1, le=1000)
    page_size: int = Field(default=20, ge=1, le=100)


class FacilityHistoryInput(BaseModel):
    facility_id: str = Field(min_length=1, max_length=64)
    limit: int = Field(default=20, ge=1, le=100)


class RagSearchToolInput(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    facility_type: str | None = Field(default=None, max_length=64)
    region: str | None = Field(default=None, max_length=100)
    version: str | None = Field(default=None, max_length=64)
    as_of_date: date | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class SlaCalculateInput(BaseModel):
    report_id: str | None = Field(default=None, max_length=64)
    issue_type: str = Field(min_length=1, max_length=64)
    priority: Literal["P1", "P2", "P3", "P4"]
    reported_at: datetime
    region: str | None = Field(default=None, max_length=100)


class StaffCapacityInput(BaseModel):
    region: str = Field(min_length=1, max_length=100)
    skill: str | None = Field(default=None, max_length=64)
    scheduled_for: date


class ReportCreateInput(BaseModel):
    description: str = Field(min_length=1, max_length=5000)
    issue_type: str = Field(min_length=1, max_length=64)
    region: str = Field(min_length=1, max_length=100)
    facility_id: str | None = Field(default=None, max_length=64)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class InspectionCreateInput(BaseModel):
    facility_id: str = Field(min_length=1, max_length=64)
    region: str = Field(min_length=1, max_length=100)
    scheduled_at: datetime
    due_at: datetime
    assignee_id: str | None = Field(default=None, max_length=64)
    priority: Literal["P1", "P2", "P3", "P4"] = "P3"


class WorkOrderCreateInput(BaseModel):
    report_id: str | None = Field(default=None, max_length=64)
    facility_id: str = Field(min_length=1, max_length=64)
    region: str = Field(min_length=1, max_length=100)
    priority: Literal["P1", "P2", "P3", "P4"]
    summary: str = Field(min_length=1, max_length=2000)


class WorkOrderAssignInput(BaseModel):
    work_order_id: str = Field(min_length=1, max_length=64)
    region: str = Field(min_length=1, max_length=100)
    assignee_id: str | None = Field(default=None, max_length=64)
    vendor_id: str | None = Field(default=None, max_length=64)


class WorkOrderStatusInput(BaseModel):
    work_order_id: str = Field(min_length=1, max_length=64)
    target_status: str = Field(min_length=1, max_length=32)
    reason: str | None = Field(default=None, max_length=2000)


class SafetyChecklistInput(BaseModel):
    facility_type: str = Field(min_length=1, max_length=64)
    issue_type: str = Field(min_length=1, max_length=64)
    work_description: str = Field(min_length=1, max_length=2000)
    region: str = Field(min_length=1, max_length=100)


class AcceptanceSubmitInput(BaseModel):
    work_order_id: str = Field(min_length=1, max_length=64)
    result: Literal["ACCEPTED", "REJECTED", "CONDITIONAL"]
    reason: str | None = Field(default=None, max_length=2000)
    evidence_uri: str | None = Field(default=None, max_length=1024)


class AuditRecordInput(BaseModel):
    action: str = Field(min_length=1, max_length=128)
    resource_type: str = Field(min_length=1, max_length=64)
    resource_id: str | None = Field(default=None, max_length=64)
    result: Literal["SUCCEEDED", "FAILED", "DENIED"]
    details: dict[str, Any] = Field(default_factory=dict)


class ItemsOutput(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)


class SingleResultOutput(BaseModel):
    item: dict[str, Any] = Field(default_factory=dict)


class RecommendationOutput(BaseModel):
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class WriteResultOutput(BaseModel):
    resource_id: str
    status: str
    duplicate: bool = False


class AuditResultOutput(BaseModel):
    audit_id: str
    recorded: bool = True


@dataclass(frozen=True)
class ToolContract:
    name: str
    description: str
    allowed_agents: tuple[AgentName, ...]
    permissions: tuple[str, ...]
    risk_level: RiskLevel
    confirmation: ConfirmationPolicy
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    error_codes: tuple[str, ...]
    retryable_error_codes: tuple[str, ...]
    idempotency_required: bool
    audit_action: str

    def json_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input": self.input_model.model_json_schema(),
            "output": self.output_model.model_json_schema(),
            "errors": list(self.error_codes),
            "retryable_errors": list(self.retryable_error_codes),
            "permissions": list(self.permissions),
            "risk_level": self.risk_level,
            "confirmation": self.confirmation,
            "idempotency_required": self.idempotency_required,
            "audit_action": self.audit_action,
        }


def _contract(
    name: str,
    description: str,
    agents: tuple[AgentName, ...],
    permissions: tuple[str, ...],
    risk: RiskLevel,
    confirmation: ConfirmationPolicy,
    input_model: type[BaseModel],
    output_model: type[BaseModel],
    errors: tuple[str, ...],
    retryable: tuple[str, ...],
    *,
    idempotent: bool,
    audit_action: str,
) -> ToolContract:
    return ToolContract(
        name,
        description,
        agents,
        permissions,
        risk,
        confirmation,
        input_model,
        output_model,
        errors,
        retryable,
        idempotent,
        audit_action,
    )


TOOL_CONTRACTS: dict[str, ToolContract] = {
    "facility.search": _contract(
        "facility.search",
        "按设施 ID、地址关键词、类型或区域查询有限分页的设施台账；用于分诊和设施识别，返回设施摘要与总数。",
        ("triage", "facility", "inspection", "dispatch"),
        ("facility:read",),
        "READ_ONLY",
        "NEVER",
        FacilitySearchInput,
        ItemsOutput,
        ("INVALID_ARGUMENT", "REGION_SCOPE_DENIED", "FACILITY_NOT_FOUND", "DATABASE_UNAVAILABLE"),
        ("DATABASE_UNAVAILABLE",),
        idempotent=False,
        audit_action="facility_search",
    ),
    "facility.history": _contract(
        "facility.history",
        "查询单个设施的报修、巡检和工单历史；用于识别重复问题和风险，返回有限事件摘要。",
        ("triage", "facility", "inspection"),
        ("facility:read",),
        "READ_ONLY",
        "NEVER",
        FacilityHistoryInput,
        ItemsOutput,
        ("INVALID_ARGUMENT", "REGION_SCOPE_DENIED", "FACILITY_NOT_FOUND", "DATABASE_UNAVAILABLE"),
        ("DATABASE_UNAVAILABLE",),
        idempotent=False,
        audit_action="facility_history",
    ),
    "rag.search": _contract(
        "rag.search",
        "检索当前有效且已索引的知识 Chunk；用于获取可定位证据，返回文档、页码、Chunk ID、相似度和片段。",
        ("supervisor", "triage", "facility", "sla", "safety", "acceptance"),
        ("document:read",),
        "READ_ONLY",
        "NEVER",
        RagSearchToolInput,
        RecommendationOutput,
        ("INVALID_ARGUMENT", "NO_RECALL", "RETRIEVAL_UNAVAILABLE", "REGION_SCOPE_DENIED"),
        ("RETRIEVAL_UNAVAILABLE",),
        idempotent=False,
        audit_action="rag_search",
    ),
    "sla.calculate": _contract(
        "sla.calculate",
        "根据问题类型、优先级和报告时间计算 SLA 截止时间；只返回确定性计算结果，不修改工单。",
        ("triage", "sla", "dispatch"),
        ("work_order:read",),
        "READ_ONLY",
        "NEVER",
        SlaCalculateInput,
        SingleResultOutput,
        ("INVALID_ARGUMENT", "SLA_RULE_NOT_FOUND", "DATABASE_UNAVAILABLE"),
        ("DATABASE_UNAVAILABLE",),
        idempotent=False,
        audit_action="sla_calculate",
    ),
    "staff.capacity": _contract(
        "staff.capacity",
        "查询指定区域、技能和日期的人员或供应商容量；用于巡检计划和派工候选，不执行分配。",
        ("inspection", "dispatch"),
        ("work_order:read",),
        "READ_ONLY",
        "NEVER",
        StaffCapacityInput,
        ItemsOutput,
        ("INVALID_ARGUMENT", "REGION_SCOPE_DENIED", "DATABASE_UNAVAILABLE"),
        ("DATABASE_UNAVAILABLE",),
        idempotent=False,
        audit_action="staff_capacity",
    ),
    "report.create": _contract(
        "report.create",
        "创建一条内部问题上报；仅在用户确认描述和区域后使用，返回报修 ID 与初始状态。",
        ("triage",),
        ("report:create",),
        "WRITE",
        "OPTIONAL",
        ReportCreateInput,
        WriteResultOutput,
        ("INVALID_ARGUMENT", "REGION_SCOPE_DENIED", "DUPLICATE_REQUEST", "DATABASE_UNAVAILABLE"),
        ("DATABASE_UNAVAILABLE",),
        idempotent=True,
        audit_action="report_create",
    ),
    "inspection.create": _contract(
        "inspection.create",
        "创建巡检任务建议；使用前必须完成日期、区域、人员容量和重复任务校验，返回巡检任务 ID。",
        ("inspection",),
        ("inspection:create",),
        "WRITE",
        "OPTIONAL",
        InspectionCreateInput,
        WriteResultOutput,
        ("INVALID_ARGUMENT", "REGION_SCOPE_DENIED", "CAPACITY_EXCEEDED", "DUPLICATE_REQUEST", "DATABASE_UNAVAILABLE"),
        ("DATABASE_UNAVAILABLE",),
        idempotent=True,
        audit_action="inspection_create",
    ),
    "work_order.create": _contract(
        "work_order.create",
        "从已确认的问题或设施创建维修工单；必须提供优先级和区域，返回工单 ID 与初始状态。",
        ("triage", "sla", "dispatch"),
        ("work_order:create",),
        "WRITE",
        "OPTIONAL",
        WorkOrderCreateInput,
        WriteResultOutput,
        ("INVALID_ARGUMENT", "REGION_SCOPE_DENIED", "FACILITY_NOT_FOUND", "DUPLICATE_REQUEST", "DATABASE_UNAVAILABLE"),
        ("DATABASE_UNAVAILABLE",),
        idempotent=True,
        audit_action="work_order_create",
    ),
    "work_order.assign": _contract(
        "work_order.assign",
        "为工单提出或执行人员/供应商派工；只有通过区域、技能、冲突和容量校验并获得人工确认后才执行。",
        ("dispatch",),
        ("work_order:write",),
        "HIGH",
        "REQUIRED",
        WorkOrderAssignInput,
        WriteResultOutput,
        (
            "INVALID_ARGUMENT",
            "REGION_SCOPE_DENIED",
            "ASSIGNEE_NOT_FOUND",
            "CAPACITY_EXCEEDED",
            "HUMAN_CONFIRMATION_REQUIRED",
            "DUPLICATE_REQUEST",
            "DATABASE_UNAVAILABLE",
        ),
        ("DATABASE_UNAVAILABLE",),
        idempotent=True,
        audit_action="work_order_assign",
    ),
    "work_order.update_status": _contract(
        "work_order.update_status",
        "按工单状态机推进或回退工单；关闭、取消和返工等高风险状态必须经过人工确认，返回状态变更结果。",
        ("triage", "dispatch", "acceptance"),
        ("work_order:write",),
        "HIGH",
        "REQUIRED",
        WorkOrderStatusInput,
        WriteResultOutput,
        (
            "INVALID_ARGUMENT",
            "REGION_SCOPE_DENIED",
            "INVALID_STATUS_TRANSITION",
            "HUMAN_CONFIRMATION_REQUIRED",
            "DUPLICATE_REQUEST",
            "DATABASE_UNAVAILABLE",
        ),
        ("DATABASE_UNAVAILABLE",),
        idempotent=True,
        audit_action="work_order_status_update",
    ),
    "safety.checklist": _contract(
        "safety.checklist",
        "根据设施和问题类型返回安全隔离、PPE、交通防护和禁止动作清单；只提供建议，不执行现场动作。",
        ("safety", "dispatch", "acceptance"),
        ("work_order:read",),
        "READ_ONLY",
        "NEVER",
        SafetyChecklistInput,
        RecommendationOutput,
        ("INVALID_ARGUMENT", "SAFETY_RULE_NOT_FOUND", "DATABASE_UNAVAILABLE"),
        ("DATABASE_UNAVAILABLE",),
        idempotent=False,
        audit_action="safety_checklist",
    ),
    "acceptance.submit": _contract(
        "acceptance.submit",
        "提交工单验收结果和证据；仅在检查项和证据齐全并得到验收人员确认后写入验收记录。",
        ("acceptance",),
        ("work_order:accept",),
        "HIGH",
        "REQUIRED",
        AcceptanceSubmitInput,
        WriteResultOutput,
        (
            "INVALID_ARGUMENT",
            "REGION_SCOPE_DENIED",
            "WORK_ORDER_NOT_READY",
            "HUMAN_CONFIRMATION_REQUIRED",
            "DUPLICATE_REQUEST",
            "DATABASE_UNAVAILABLE",
        ),
        ("DATABASE_UNAVAILABLE",),
        idempotent=True,
        audit_action="acceptance_submit",
    ),
    "audit.record": _contract(
        "audit.record",
        "记录 Agent 或工具动作的最小审计摘要；高风险工具必须先记录授权和确认信息，返回审计 ID。",
        ("supervisor", "triage", "facility", "sla", "inspection", "dispatch", "safety", "acceptance"),
        ("audit:write",),
        "WRITE",
        "NEVER",
        AuditRecordInput,
        AuditResultOutput,
        ("INVALID_ARGUMENT", "AUDIT_WRITE_FAILED"),
        (),
        idempotent=True,
        audit_action="audit_record",
    ),
}


AGENT_TOOL_WHITELIST: dict[AgentName, tuple[str, ...]] = {
    agent: tuple(name for name, contract in TOOL_CONTRACTS.items() if agent in contract.allowed_agents)
    for agent in ("supervisor", "triage", "facility", "sla", "inspection", "dispatch", "safety", "acceptance")
}


def get_tool_contract(tool_name: str) -> ToolContract:
    try:
        return TOOL_CONTRACTS[tool_name]
    except KeyError as exc:
        raise KeyError(f"unknown agent tool: {tool_name}") from exc


def validate_contract_catalog() -> None:
    for name, contract in TOOL_CONTRACTS.items():
        if name != contract.name or "." not in name:
            raise ValueError(f"invalid tool name: {name}")
        if contract.risk_level == "HIGH" and contract.confirmation != "REQUIRED":
            raise ValueError(f"high-risk tool requires confirmation: {name}")
        if contract.risk_level != "READ_ONLY" and not contract.idempotency_required:
            raise ValueError(f"write tool requires idempotency: {name}")
        if not contract.error_codes:
            raise ValueError(f"tool has no error contract: {name}")


def tool_catalog() -> list[dict[str, Any]]:
    validate_contract_catalog()
    return [TOOL_CONTRACTS[name].json_schema() for name in sorted(TOOL_CONTRACTS)]


validate_contract_catalog()
