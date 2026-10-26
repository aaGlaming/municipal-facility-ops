from datetime import datetime

import pytest

from scripts.seed_database import SeedValidationError, validate_seed_plan


def _valid_plan() -> dict[str, list[dict[str, object]]]:
    plan = {
        "locations": [{"id": 1, "external_id": "LOC-00001"}],
        "facilities": [{"id": "FAC-00001", "location_id": 1}],
        "technicians": [{"id": "TECH-0001"}],
        "vendors": [{"id": "VEN-0001"}],
        "sla_rules": [{"id": "SLA-1"}],
        "citizen_reports": [{"id": "RPT-000001", "facility_id": "FAC-00001", "status": "NEW"}],
        "inspection_tasks": [
            {
                "id": "INS-000001",
                "facility_id": "FAC-00001",
                "assignee_id": "TECH-0001",
                "scheduled_at": datetime(2026, 1, 1),
                "completed_at": datetime(2026, 1, 1, 8),
                "status": "COMPLETED",
            }
        ],
        "work_orders": [
            {
                "id": "WO-000001",
                "facility_id": "FAC-00001",
                "report_id": "RPT-000001",
                "assignee_id": "TECH-0001",
                "vendor_id": "VEN-0001",
                "created_at": datetime(2026, 1, 1),
                "due_at": datetime(2026, 1, 2),
                "status": "NEW",
                "idempotency_key": "wo-1",
            }
        ],
        "acceptance_records": [{"id": "ACC-000001", "work_order_id": "WO-000001"}],
        "agent_runs": [{"id": "RUN-000001"}],
        "audit_logs": [{"id": "AUD-000001", "agent_run_id": "RUN-000001"}],
    }
    for table in {
        "locations",
        "facilities",
        "technicians",
        "vendors",
        "sla_rules",
        "citizen_reports",
        "inspection_tasks",
        "work_orders",
        "acceptance_records",
        "agent_runs",
    }:
        for row in plan[table]:
            row.update({"source_type": "synthetic", "source_system": "test", "data_version": "v1"})
    return plan


def test_validate_seed_plan_accepts_foreign_keys_and_time_order() -> None:
    report = validate_seed_plan(_valid_plan())
    assert report["rows"] == {key: len(value) for key, value in _valid_plan().items()}
    assert report["errors"] == []


def test_validate_seed_plan_rejects_missing_foreign_key_and_duplicate_idempotency() -> None:
    plan = _valid_plan()
    plan["work_orders"].append(
        {
            "id": "WO-000002",
            "facility_id": "FAC-MISSING",
            "report_id": "RPT-000001",
            "created_at": datetime(2026, 1, 2),
            "due_at": datetime(2026, 1, 1),
            "status": "BROKEN",
            "idempotency_key": "wo-1",
        }
    )
    with pytest.raises(SeedValidationError) as caught:
        validate_seed_plan(plan)
    message = str(caught.value)
    assert "work_orders.facility_id" in message
    assert "work_orders.due_at" in message
    assert "work_orders.status" in message
    assert "idempotency_key" in message
