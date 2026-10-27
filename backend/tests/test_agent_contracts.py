from datetime import datetime

import pytest
from app.memory.state import initial_agent_state
from app.schemas.agent import AgentRequest, ToolCallRequest, build_idempotency_key
from app.tools.contracts import (
    AGENT_TOOL_WHITELIST,
    TOOL_CONTRACTS,
    get_tool_contract,
    tool_catalog,
    validate_contract_catalog,
)


def _request() -> AgentRequest:
    return AgentRequest(
        request_id="REQ-1",
        trace_id="TRACE-1",
        session_id="SESSION-1",
        user_id="USER-1",
        agent_name="triage",
        intent="识别设施",
        input={"description": "路灯不亮"},
    )


def test_agent_state_contains_bounded_graph_fields() -> None:
    state = initial_agent_state(_request(), "RUN-1", datetime(2026, 10, 27, 12, 0, 0))
    assert state["status"] == "PENDING"
    assert state["model_calls"] == 0
    assert state["tool_calls"] == 0
    assert state["observations"] == []
    assert state["evidence"] == []
    assert state["pending_confirmation"] is None


def test_idempotency_key_is_stable_and_tool_request_is_strict() -> None:
    first = build_idempotency_key("TRACE-1", "work_order.create", "REPORT-1", {"priority": "P2"})
    second = build_idempotency_key("TRACE-1", "work_order.create", "REPORT-1", {"priority": "P2"})
    assert first == second
    assert first != build_idempotency_key("TRACE-1", "work_order.create", "REPORT-1", {"priority": "P1"})
    request = ToolCallRequest(
        tool_call_id="CALL-1",
        agent_run_id="RUN-1",
        trace_id="TRACE-1",
        agent_name="triage",
        tool_name="work_order.create",
        arguments={"priority": "P2"},
        idempotency_key=first,
    )
    assert request.tool_name == "work_order.create"
    with pytest.raises(ValueError):
        ToolCallRequest(
            tool_call_id="CALL-2",
            agent_run_id="RUN-1",
            trace_id="TRACE-1",
            tool_name="work-order-create",
            idempotency_key=first,
        )


def test_tool_catalog_has_schema_whitelist_risk_and_failure_policy() -> None:
    validate_contract_catalog()
    catalog = tool_catalog()
    assert len(catalog) == len(TOOL_CONTRACTS) == 16
    assert all(item["input"] and item["output"] for item in catalog)
    assert set(AGENT_TOOL_WHITELIST) == {
        "supervisor",
        "triage",
        "facility",
        "sla",
        "inspection",
        "dispatch",
        "safety",
        "acceptance",
    }
    for name, contract in TOOL_CONTRACTS.items():
        assert get_tool_contract(name) is contract
        assert contract.error_codes
        if contract.risk_level == "HIGH":
            assert contract.confirmation == "REQUIRED"
        if contract.risk_level != "READ_ONLY":
            assert contract.idempotency_required


def test_unknown_tool_contract_is_rejected() -> None:
    with pytest.raises(KeyError):
        get_tool_contract("unknown.tool")
