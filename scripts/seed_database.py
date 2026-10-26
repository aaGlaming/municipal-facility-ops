import argparse
import csv
import hashlib
import json
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import pymysql  # type: ignore[import-untyped]

REPORT_STATUSES = {"NEW", "OPEN", "TRIAGED", "ASSIGNED", "IN_PROGRESS", "PENDING", "CLOSED"}
INSPECTION_STATUSES = {"SCHEDULED", "IN_PROGRESS", "COMPLETED", "CANCELLED"}
WORK_ORDER_STATUSES = {
    "NEW",
    "TRIAGED",
    "ASSIGNED",
    "IN_PROGRESS",
    "WAITING_CONFIRMATION",
    "COMPLETED",
    "ACCEPTED",
    "CLOSED",
}
ACCEPTANCE_RESULTS = {"ACCEPTED", "CONDITIONAL_ACCEPTANCE", "REWORK_REQUIRED"}
SOURCE_TYPES = {"public", "synthetic", "internal"}


class SeedValidationError(ValueError):
    pass


class SeedImportError(RuntimeError):
    pass


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def _text(row: dict[str, str], key: str, default: str = "") -> str:
    return (row.get(key) or default).strip()


def _parse_datetime(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    candidate = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(candidate)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def _parse_date(value: str) -> str | None:
    value = value.strip()
    return value or None


def _to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _to_float(value: str) -> float | None:
    return float(value) if value.strip() else None


def _source_meta(row: dict[str, str], fallback: str) -> dict[str, str]:
    source_type = _text(row, "source_type", fallback)
    generator_version = _text(row, "generator_version", _text(row, "mapping_version", "v1"))
    return {
        "source_type": source_type,
        "source_system": fallback,
        "data_version": generator_version,
    }


def _status(value: str) -> str:
    return value.strip().upper().replace(" ", "_") or "UNKNOWN"


def _id_number(value: str) -> int:
    return int(value.rsplit("-", 1)[-1])


def _hash_event(batch_id: str, audit_id: int, run_id: str, action: str) -> str:
    return hashlib.sha256(f"{batch_id}|{audit_id}|{run_id}|{action}".encode()).hexdigest()


def _make_roles_and_permissions() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    role_specs = [
        ("ROLE-ADMIN", "admin", "平台管理员"),
        ("ROLE-DISPATCHER", "dispatcher", "调度员"),
        ("ROLE-INSPECTOR", "inspector", "巡检员"),
        ("ROLE-TECHNICIAN", "technician", "维修人员"),
        ("ROLE-AUDITOR", "auditor", "审计人员"),
    ]
    permission_specs = [
        ("PERM-FACILITY-READ", "facility:read"),
        ("PERM-REPORT-WRITE", "report:write"),
        ("PERM-WORK-ORDER-READ", "work_order:read"),
        ("PERM-WORK-ORDER-WRITE", "work_order:write"),
        ("PERM-AUDIT-READ", "audit:read"),
    ]
    roles = [
        {
            "id": role_id,
            "role_code": code,
            "name": name,
            "description": name,
            "source_type": "internal",
            "source_system": "seed",
            "data_version": "step09-v1",
            "version": 1,
            "is_deleted": False,
        }
        for role_id, code, name in role_specs
    ]
    permissions = [
        {
            "id": permission_id,
            "permission_code": code,
            "description": code,
            "source_type": "internal",
            "source_system": "seed",
            "data_version": "step09-v1",
            "version": 1,
            "is_deleted": False,
        }
        for permission_id, code in permission_specs
    ]
    role_permissions = [
        {"role_id": "ROLE-ADMIN", "permission_id": permission_id} for permission_id, _ in permission_specs
    ] + [
        {"role_id": "ROLE-DISPATCHER", "permission_id": "PERM-FACILITY-READ"},
        {"role_id": "ROLE-DISPATCHER", "permission_id": "PERM-REPORT-WRITE"},
        {"role_id": "ROLE-DISPATCHER", "permission_id": "PERM-WORK-ORDER-READ"},
        {"role_id": "ROLE-DISPATCHER", "permission_id": "PERM-WORK-ORDER-WRITE"},
        {"role_id": "ROLE-INSPECTOR", "permission_id": "PERM-FACILITY-READ"},
        {"role_id": "ROLE-TECHNICIAN", "permission_id": "PERM-WORK-ORDER-READ"},
        {"role_id": "ROLE-AUDITOR", "permission_id": "PERM-AUDIT-READ"},
    ]
    return roles, permissions, role_permissions


def build_seed_plan(data_root: Path = Path("data"), batch_id: str = "step09-local") -> dict[str, list[dict[str, Any]]]:
    synthetic = data_root / "synthetic"
    processed = data_root / "processed"
    facilities_source = _read_csv(synthetic / "synthetic_facilities.csv")
    locations_source = _read_csv(synthetic / "synthetic_locations.csv")
    technicians_source = _read_csv(synthetic / "synthetic_technicians.csv")
    vendors_source = _read_csv(synthetic / "synthetic_vendors.csv")
    sla_source = _read_csv(synthetic / "synthetic_sla_rules.csv")
    reports_source = _read_csv(synthetic / "synthetic_citizen_reports.csv")
    inspections_source = _read_csv(synthetic / "synthetic_inspection_tasks.csv")
    orders_source = _read_csv(synthetic / "synthetic_work_orders.csv")
    acceptances_source = _read_csv(synthetic / "synthetic_acceptance_records.csv")
    runs_source = _read_csv(synthetic / "synthetic_agent_runs.csv")
    audits_source = _read_csv(synthetic / "synthetic_audit_logs.csv")
    public_source = _read_csv(processed / "facility_issue_events.csv")

    roles, permissions, role_permissions = _make_roles_and_permissions()
    users = [
        {
            "id": row["technician_id"],
            "username": row["technician_id"].lower(),
            "email": f"{row['technician_id'].lower()}@synthetic.local",
            "display_name": row["technician_name"],
            "password_hash": None,
            "status": "active" if _to_bool(row["active"]) else "inactive",
            "region": row["team_id"],
            "source_type": "synthetic",
            "source_system": "synthetic-v2",
            "data_version": _text(row, "generator_version", "synthetic-v2"),
            "version": 1,
            "is_deleted": False,
        }
        for row in technicians_source
    ]
    user_roles = [{"user_id": row["technician_id"], "role_id": "ROLE-TECHNICIAN"} for row in technicians_source]

    locations = [
        {
            "id": _id_number(row["location_id"]),
            "address": row["address"],
            "district": row["district"],
            "region": row["district"],
            "longitude": _to_float(row["longitude"]),
            "latitude": _to_float(row["latitude"]),
            "external_id": row["location_id"],
            **_source_meta(row, "synthetic-v2"),
            "version": 1,
            "is_deleted": False,
        }
        for row in locations_source
    ]
    facilities = [
        {
            "id": row["facility_id"],
            "facility_code": row["facility_code"],
            "type": row["facility_type"],
            "name": row["facility_name"],
            "status": "active",
            "criticality": row["criticality"],
            "location_id": _id_number(row["facility_id"]),
            "region": row["borough"],
            "external_id": row["facility_id"],
            "install_date": _parse_date(row["install_date"]),
            "condition_score": int(row["condition_score"]),
            **_source_meta(row, "synthetic-v2"),
            "version": 1,
            "is_deleted": False,
        }
        for row in facilities_source
    ]
    technicians = [
        {
            "id": row["technician_id"],
            "name": row["technician_name"],
            "team": row["team_id"],
            "skill": row["primary_skill"],
            "region": row["team_id"],
            "active": _to_bool(row["active"]),
            **_source_meta(row, "synthetic-v2"),
            "version": 1,
            "is_deleted": False,
        }
        for row in technicians_source
    ]
    vendors = [
        {
            "id": row["vendor_id"],
            "name": row["vendor_name"],
            "capabilities": json.dumps(
                {"service_scope": row["service_scope"], "rating": row["rating"], "contact_phone": row["contact_phone"]}
            ),
            "sla_level": row["service_scope"],
            "region": None,
            "active": _to_bool(row["active"]),
            **_source_meta(row, "synthetic-v2"),
            "version": 1,
            "is_deleted": False,
        }
        for row in vendors_source
    ]
    sla_rules = [
        {
            "id": row["sla_rule_id"],
            "category": row["facility_type"],
            "priority": row["priority"],
            "response_minutes": int(float(row["first_response_hours"]) * 60),
            "resolution_minutes": int(float(row["resolution_hours"]) * 60),
            "escalation_minutes": int(float(row["escalation_after_hours"]) * 60),
            "region": None,
            **_source_meta(row, "synthetic-v2"),
            "version": 1,
            "is_deleted": False,
        }
        for row in sla_source
    ]
    citizen_reports = []
    for row in public_source:
        event_id = f"PUB-{row['event_id']}"
        citizen_reports.append(
            {
                "id": event_id,
                "facility_id": None,
                "reporter_user_id": None,
                "source": row["source_dataset"],
                "description": row["description"] or row["category"],
                "category": row["category"],
                "subcategory": row["subcategory"],
                "status": _status(row["status"]),
                "priority": None,
                "external_id": row["external_id"],
                "source_type": "public",
                "source_system": row["source_dataset"],
                "data_version": row["mapping_version"],
                "region": row["borough"],
                "latitude": _to_float(row["latitude"]),
                "longitude": _to_float(row["longitude"]),
                "idempotency_key": f"public:{row['source_dataset']}:{row['external_id']}:{row['source_row_number']}",
                "reported_at": _parse_datetime(row["created_at"]),
                "due_at": None,
                "version": 1,
                "is_deleted": False,
            }
        )
    for row in reports_source:
        citizen_reports.append(
            {
                "id": row["report_id"],
                "facility_id": row["facility_id"],
                "reporter_user_id": None,
                "source": row["channel"],
                "description": row["description"],
                "category": row["category"],
                "subcategory": None,
                "status": _status(row["status"]),
                "priority": None,
                "external_id": row["report_id"],
                "source_type": "synthetic",
                "source_system": "synthetic-v2",
                "data_version": row["generator_version"],
                "region": None,
                "latitude": None,
                "longitude": None,
                "idempotency_key": f"synthetic:report:{row['report_id']}",
                "reported_at": _parse_datetime(row["reported_at"]),
                "due_at": None,
                "version": 1,
                "is_deleted": False,
            }
        )
    inspections = [
        {
            "id": row["inspection_id"],
            "facility_id": row["facility_id"],
            "area": row["notes"],
            "priority": "P1" if row["severity"] == "critical" else "P3",
            "scheduled_at": _parse_datetime(row["scheduled_at"]),
            "due_at": _parse_datetime(row["completed_at"]),
            "completed_at": _parse_datetime(row["completed_at"]),
            "assignee_id": row["inspector_id"],
            "status": "COMPLETED",
            "region": None,
            **_source_meta(row, "synthetic-v2"),
            "version": 1,
            "is_deleted": False,
        }
        for row in inspections_source
    ]
    work_orders = [
        {
            "id": row["work_order_id"],
            "report_id": row["report_id"],
            "facility_id": row["facility_id"],
            "priority": row["priority"],
            "problem_type": row["problem_type"],
            "assignee_id": row["assigned_technician_id"],
            "vendor_id": row["vendor_id"],
            "due_at": _parse_datetime(row["due_at"]),
            "completed_at": _parse_datetime(row["completed_at"]),
            "status": _status(row["status"]),
            "idempotency_key": row["idempotency_key"],
            "region": None,
            **_source_meta(row, "synthetic-v2"),
            "version": 1,
            "is_deleted": False,
            "created_at": _parse_datetime(row["created_at"]),
        }
        for row in orders_source
    ]
    acceptance_records = [
        {
            "id": row["acceptance_id"],
            "work_order_id": row["work_order_id"],
            "reviewer_id": row["reviewer_id"],
            "result": _status(row["result"]),
            "reason": row["comments"],
            "evidence_uri": row["evidence_uri"],
            **_source_meta(row, "synthetic-v2"),
            "version": 1,
            "is_deleted": False,
            "created_at": _parse_datetime(row["accepted_at"]),
        }
        for row in acceptances_source
    ]
    agent_runs = [
        {
            "id": row["run_id"],
            "agent_name": row["agent_name"],
            "trace_id": f"trace-{row['run_id']}",
            "user_id": None,
            "region": None,
            "status": _status(row["status"]),
            "iterations": int(row["iterations"]),
            "input_tokens": int(row["input_tokens"]),
            "output_tokens": int(row["output_tokens"]),
            "model_version": None,
            "prompt_version": row["generator_version"],
            "stop_reason": row["status"],
            **_source_meta(row, "synthetic-v2"),
            "version": 1,
            "is_deleted": False,
            "started_at": _parse_datetime(row["started_at"]),
            "finished_at": _parse_datetime(row["finished_at"]),
        }
        for row in runs_source
    ]
    audit_logs = []
    previous_hash: str | None = None
    for row in audits_source:
        audit_id = _id_number(row["audit_id"])
        event_hash = _hash_event(batch_id, audit_id, row["run_id"], row["action"])
        audit_logs.append(
            {
                "id": audit_id,
                "actor_user_id": None,
                "actor": row["actor"],
                "agent_run_id": row["run_id"],
                "tool_call_id": None,
                "tool_name": None,
                "action": row["action"],
                "resource_type": row["target_type"],
                "resource_id": row["target_id"],
                "before_json": None,
                "after_json": row["detail"],
                "result": _status(row["result"]),
                "risk_level": "medium" if row["action"] in {"assign", "acceptance"} else "low",
                "error": None,
                "human_confirmation": row["result"] == "waiting_confirmation",
                "event_version": row["generator_version"],
                "event_hash": event_hash,
                "previous_event_hash": previous_hash,
                "created_at": _parse_datetime(row["created_at"]),
            }
        )
        previous_hash = event_hash
    plan = {
        "roles": roles,
        "permissions": permissions,
        "role_permissions": role_permissions,
        "users": users,
        "user_roles": user_roles,
        "locations": locations,
        "facilities": facilities,
        "technicians": technicians,
        "vendors": vendors,
        "sla_rules": sla_rules,
        "citizen_reports": citizen_reports,
        "inspection_tasks": inspections,
        "work_orders": work_orders,
        "acceptance_records": acceptance_records,
        "agent_runs": agent_runs,
        "tool_calls": [],
        "audit_logs": audit_logs,
    }
    validate_seed_plan(plan)
    return plan


def _ids(plan: dict[str, list[dict[str, Any]]], table: str) -> set[Any]:
    return {row["id"] for row in plan.get(table, []) if "id" in row}


def validate_seed_plan(plan: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    errors: list[str] = []
    rows = {key: len(value) for key, value in plan.items()}
    metadata_tables = {
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
    }
    for table, values in plan.items():
        if "id" not in values[0] if values else False:
            continue
        ids = [row["id"] for row in values]
        duplicates = [key for key, count in Counter(ids).items() if count > 1]
        if duplicates:
            errors.append(f"{table}.duplicate_id:{duplicates[:3]}")
        if table in metadata_tables:
            for row in values:
                if row.get("source_type") not in SOURCE_TYPES:
                    errors.append(f"{table}.source_type:{row.get('id')}->{row.get('source_type')}")
                if not row.get("source_system") or not row.get("data_version"):
                    errors.append(f"{table}.source_metadata:{row.get('id')}")
    facility_ids = _ids(plan, "facilities")
    location_ids = _ids(plan, "locations")
    technician_ids = _ids(plan, "technicians")
    vendor_ids = _ids(plan, "vendors")
    report_ids = _ids(plan, "citizen_reports")
    work_order_ids = _ids(plan, "work_orders")
    run_ids = _ids(plan, "agent_runs")
    for row in plan.get("facilities", []):
        if row.get("location_id") not in location_ids:
            errors.append(f"facilities.location_id:{row.get('id')}->{row.get('location_id')}")
    for row in plan.get("citizen_reports", []):
        if row.get("facility_id") and row["facility_id"] not in facility_ids:
            errors.append(f"citizen_reports.facility_id:{row.get('id')}->{row.get('facility_id')}")
        if row.get("status") and row["status"] not in REPORT_STATUSES and row["status"] != "UNKNOWN":
            errors.append(f"citizen_reports.status:{row.get('id')}->{row.get('status')}")
    for row in plan.get("inspection_tasks", []):
        if row.get("facility_id") not in facility_ids:
            errors.append(f"inspection_tasks.facility_id:{row.get('id')}->{row.get('facility_id')}")
        if row.get("assignee_id") and row["assignee_id"] not in technician_ids:
            errors.append(f"inspection_tasks.assignee_id:{row.get('id')}->{row.get('assignee_id')}")
        if row.get("scheduled_at") and row.get("completed_at") and row["completed_at"] < row["scheduled_at"]:
            errors.append(f"inspection_tasks.time_order:{row.get('id')}")
        if row.get("status") not in INSPECTION_STATUSES:
            errors.append(f"inspection_tasks.status:{row.get('id')}->{row.get('status')}")
    idempotency_keys: list[str] = []
    for row in plan.get("work_orders", []):
        idempotency_keys.append(str(row.get("idempotency_key")))
        for field, valid_ids in (
            ("facility_id", facility_ids),
            ("report_id", report_ids),
            ("assignee_id", technician_ids),
            ("vendor_id", vendor_ids),
        ):
            if row.get(field) and row[field] not in valid_ids:
                errors.append(f"work_orders.{field}:{row.get('id')}->{row.get(field)}")
        if row.get("created_at") and row.get("due_at") and row["due_at"] < row["created_at"]:
            errors.append(f"work_orders.due_at:{row.get('id')}")
        if row.get("status") not in WORK_ORDER_STATUSES:
            errors.append(f"work_orders.status:{row.get('id')}->{row.get('status')}")
    duplicate_keys = [key for key, count in Counter(idempotency_keys).items() if count > 1]
    if duplicate_keys:
        errors.append(f"work_orders.idempotency_key:{duplicate_keys[:3]}")
    for row in plan.get("acceptance_records", []):
        if row.get("work_order_id") not in work_order_ids:
            errors.append(f"acceptance_records.work_order_id:{row.get('id')}->{row.get('work_order_id')}")
        if row.get("reviewer_id") and row["reviewer_id"] not in {user["id"] for user in plan.get("users", [])}:
            errors.append(f"acceptance_records.reviewer_id:{row.get('id')}->{row.get('reviewer_id')}")
        if row.get("result") and row["result"] not in ACCEPTANCE_RESULTS:
            errors.append(f"acceptance_records.result:{row.get('id')}->{row.get('result')}")
    for row in plan.get("audit_logs", []):
        if row.get("agent_run_id") not in run_ids:
            errors.append(f"audit_logs.agent_run_id:{row.get('id')}->{row.get('agent_run_id')}")
    if errors:
        raise SeedValidationError("; ".join(errors[:20]))
    return {"rows": rows, "errors": errors}


def _connection_args(url: str) -> dict[str, object]:
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": parsed.port or 3306,
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": parsed.path.lstrip("/"),
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": False,
    }


def _insert_many(
    cursor: Any,
    table: str,
    rows: list[dict[str, Any]],
    columns: list[str],
    update_columns: list[str],
    chunk_size: int,
    ignore_duplicates: bool = False,
) -> None:
    if not rows:
        return
    placeholders = ",".join(["%s"] * len(columns))
    updates = ",".join(f"{column}=VALUES({column})" for column in update_columns) or f"{columns[0]}={columns[0]}"
    insert_prefix = "INSERT IGNORE" if ignore_duplicates else "INSERT"
    suffix = "" if ignore_duplicates else f" ON DUPLICATE KEY UPDATE {updates}"
    query = f"{insert_prefix} INTO {table} ({','.join(columns)}) VALUES ({placeholders}){suffix}"
    for start in range(0, len(rows), chunk_size):
        chunk = rows[start : start + chunk_size]
        cursor.executemany(query, [tuple(row.get(column) for column in columns) for row in chunk])


def _import_tables(plan: dict[str, list[dict[str, Any]]], cursor: Any, chunk_size: int) -> None:
    specs: list[tuple[str, list[str], list[str]]] = [
        (
            "roles",
            [
                "id",
                "role_code",
                "name",
                "description",
                "source_type",
                "source_system",
                "data_version",
                "version",
                "is_deleted",
            ],
            ["role_code", "name", "description"],
        ),
        (
            "permissions",
            [
                "id",
                "permission_code",
                "description",
                "source_type",
                "source_system",
                "data_version",
                "version",
                "is_deleted",
            ],
            ["permission_code", "description"],
        ),
        ("role_permissions", ["role_id", "permission_id"], []),
        (
            "users",
            [
                "id",
                "username",
                "email",
                "display_name",
                "password_hash",
                "status",
                "region",
                "source_type",
                "source_system",
                "data_version",
                "version",
                "is_deleted",
            ],
            ["username", "email", "display_name", "status", "region", "data_version", "version", "is_deleted"],
        ),
        ("user_roles", ["user_id", "role_id"], []),
        (
            "locations",
            [
                "id",
                "address",
                "district",
                "region",
                "longitude",
                "latitude",
                "external_id",
                "source_type",
                "source_system",
                "data_version",
                "version",
                "is_deleted",
            ],
            [
                "address",
                "district",
                "region",
                "longitude",
                "latitude",
                "external_id",
                "source_type",
                "source_system",
                "data_version",
                "version",
                "is_deleted",
            ],
        ),
        (
            "facilities",
            [
                "id",
                "facility_code",
                "type",
                "name",
                "status",
                "criticality",
                "location_id",
                "region",
                "external_id",
                "install_date",
                "condition_score",
                "source_type",
                "source_system",
                "data_version",
                "version",
                "is_deleted",
            ],
            [
                "facility_code",
                "type",
                "name",
                "status",
                "criticality",
                "location_id",
                "region",
                "external_id",
                "install_date",
                "condition_score",
                "source_type",
                "source_system",
                "data_version",
                "version",
                "is_deleted",
            ],
        ),
        (
            "technicians",
            [
                "id",
                "name",
                "team",
                "skill",
                "region",
                "active",
                "source_type",
                "source_system",
                "data_version",
                "version",
                "is_deleted",
            ],
            [
                "name",
                "team",
                "skill",
                "region",
                "active",
                "source_type",
                "source_system",
                "data_version",
                "version",
                "is_deleted",
            ],
        ),
        (
            "vendors",
            [
                "id",
                "name",
                "capabilities",
                "sla_level",
                "region",
                "active",
                "source_type",
                "source_system",
                "data_version",
                "version",
                "is_deleted",
            ],
            [
                "name",
                "capabilities",
                "sla_level",
                "region",
                "active",
                "source_type",
                "source_system",
                "data_version",
                "version",
                "is_deleted",
            ],
        ),
        (
            "sla_rules",
            [
                "id",
                "category",
                "priority",
                "response_minutes",
                "resolution_minutes",
                "escalation_minutes",
                "region",
                "source_type",
                "source_system",
                "data_version",
                "version",
                "is_deleted",
            ],
            [
                "category",
                "priority",
                "response_minutes",
                "resolution_minutes",
                "escalation_minutes",
                "region",
                "source_type",
                "source_system",
                "data_version",
                "version",
                "is_deleted",
            ],
        ),
        (
            "citizen_reports",
            [
                "id",
                "facility_id",
                "reporter_user_id",
                "source",
                "description",
                "category",
                "subcategory",
                "status",
                "priority",
                "external_id",
                "source_type",
                "source_system",
                "data_version",
                "region",
                "latitude",
                "longitude",
                "idempotency_key",
                "reported_at",
                "due_at",
                "version",
                "is_deleted",
            ],
            [
                "facility_id",
                "reporter_user_id",
                "source",
                "description",
                "category",
                "subcategory",
                "status",
                "priority",
                "external_id",
                "source_type",
                "source_system",
                "data_version",
                "region",
                "latitude",
                "longitude",
                "idempotency_key",
                "reported_at",
                "due_at",
                "version",
                "is_deleted",
            ],
        ),
        (
            "inspection_tasks",
            [
                "id",
                "facility_id",
                "area",
                "priority",
                "scheduled_at",
                "due_at",
                "completed_at",
                "assignee_id",
                "status",
                "region",
                "source_type",
                "source_system",
                "data_version",
                "version",
                "is_deleted",
            ],
            [
                "facility_id",
                "area",
                "priority",
                "scheduled_at",
                "due_at",
                "completed_at",
                "assignee_id",
                "status",
                "region",
                "source_type",
                "source_system",
                "data_version",
                "version",
                "is_deleted",
            ],
        ),
        (
            "work_orders",
            [
                "id",
                "report_id",
                "facility_id",
                "priority",
                "problem_type",
                "assignee_id",
                "vendor_id",
                "due_at",
                "completed_at",
                "status",
                "idempotency_key",
                "region",
                "source_type",
                "source_system",
                "data_version",
                "version",
                "is_deleted",
                "created_at",
            ],
            [
                "report_id",
                "facility_id",
                "priority",
                "problem_type",
                "assignee_id",
                "vendor_id",
                "due_at",
                "completed_at",
                "status",
                "idempotency_key",
                "region",
                "source_type",
                "source_system",
                "data_version",
                "version",
                "is_deleted",
                "created_at",
            ],
        ),
        (
            "acceptance_records",
            [
                "id",
                "work_order_id",
                "reviewer_id",
                "result",
                "reason",
                "evidence_uri",
                "source_type",
                "source_system",
                "data_version",
                "version",
                "is_deleted",
                "created_at",
            ],
            [
                "work_order_id",
                "reviewer_id",
                "result",
                "reason",
                "evidence_uri",
                "source_type",
                "source_system",
                "data_version",
                "version",
                "is_deleted",
                "created_at",
            ],
        ),
        (
            "agent_runs",
            [
                "id",
                "agent_name",
                "trace_id",
                "user_id",
                "region",
                "status",
                "iterations",
                "input_tokens",
                "output_tokens",
                "model_version",
                "prompt_version",
                "stop_reason",
                "source_type",
                "source_system",
                "data_version",
                "version",
                "is_deleted",
                "started_at",
                "finished_at",
            ],
            [
                "agent_name",
                "trace_id",
                "user_id",
                "region",
                "status",
                "iterations",
                "input_tokens",
                "output_tokens",
                "model_version",
                "prompt_version",
                "stop_reason",
                "source_type",
                "source_system",
                "data_version",
                "version",
                "is_deleted",
                "started_at",
                "finished_at",
            ],
        ),
        (
            "audit_logs",
            [
                "id",
                "actor_user_id",
                "actor",
                "agent_run_id",
                "tool_call_id",
                "tool_name",
                "action",
                "resource_type",
                "resource_id",
                "before_json",
                "after_json",
                "result",
                "risk_level",
                "error",
                "human_confirmation",
                "event_version",
                "event_hash",
                "previous_event_hash",
                "created_at",
            ],
            [
                "actor_user_id",
                "actor",
                "agent_run_id",
                "tool_call_id",
                "tool_name",
                "action",
                "resource_type",
                "resource_id",
                "before_json",
                "after_json",
                "result",
                "risk_level",
                "error",
                "human_confirmation",
                "event_version",
                "event_hash",
                "previous_event_hash",
                "created_at",
            ],
        ),
    ]
    for table, columns, update_columns in specs:
        _insert_many(
            cursor,
            table,
            plan.get(table, []),
            columns,
            update_columns,
            chunk_size,
            ignore_duplicates=table == "audit_logs",
        )


def import_seed_plan(
    plan: dict[str, list[dict[str, Any]]], url: str, batch_id: str, log_path: Path, chunk_size: int = 500
) -> dict[str, Any]:
    validation = validate_seed_plan(plan)
    report: dict[str, Any] = {
        "batch_id": batch_id,
        "started_at": datetime.now(UTC).isoformat(),
        "rows": validation["rows"],
        "status": "failed",
    }
    connection = pymysql.connect(**_connection_args(url))
    try:
        with connection.cursor() as cursor:
            _import_tables(plan, cursor, chunk_size)
        connection.commit()
        report["status"] = "completed"
        report["finished_at"] = datetime.now(UTC).isoformat()
        report["validation"] = validation
        return report
    except Exception as exc:
        connection.rollback()
        report["finished_at"] = datetime.now(UTC).isoformat()
        report["error"] = str(exc)
        raise SeedImportError(f"seed batch {batch_id} rolled back: {exc}") from exc
    finally:
        connection.close()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(report, ensure_ascii=False) + "\n")


def _register_log_manifest(log_path: Path, manifest_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"files": {}}
    payload = log_path.read_bytes()
    manifest.setdefault("files", {})["seed_imports"] = {
        **manifest.get("files", {}).get("seed_imports", {}),
        "name": "seed_imports",
        "kind": "processed",
        "path": log_path.as_posix().replace("\\", "/"),
        "rows": len(log_path.read_text(encoding="utf-8").splitlines()),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and import municipal database seed data")
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument(
        "--url", default=os.getenv("MYSQL_URL", "mysql+pymysql://municipal:municipal_dev@127.0.0.1:3306/municipal_ops")
    )
    parser.add_argument("--batch-id", default=f"seed-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}")
    parser.add_argument("--log", type=Path, default=Path("data/manifests/seed_imports.jsonl"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/manifest.json"))
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    plan = build_seed_plan(args.data_root, args.batch_id)
    validation = validate_seed_plan(plan)
    if args.dry_run:
        print(
            json.dumps({"batch_id": args.batch_id, "status": "validated", **validation}, ensure_ascii=False, indent=2)
        )
        return
    report = import_seed_plan(plan, args.url, args.batch_id, args.log, args.chunk_size)
    _register_log_manifest(args.log, args.manifest)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
