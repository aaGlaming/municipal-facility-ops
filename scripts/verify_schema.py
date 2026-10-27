import argparse
import json
import os
from urllib.parse import unquote, urlparse

import pymysql  # type: ignore[import-untyped]

REQUIRED_TABLES = {
    "users",
    "roles",
    "permissions",
    "role_permissions",
    "user_roles",
    "locations",
    "facilities",
    "citizen_reports",
    "inspection_tasks",
    "work_orders",
    "vendors",
    "technicians",
    "sla_rules",
    "acceptance_records",
    "work_order_status_events",
    "documents",
    "document_parts",
    "document_chunks",
    "agent_runs",
    "tool_calls",
    "audit_logs",
}
REQUIRED_COLUMNS = {
    "facilities": {
        "id",
        "facility_code",
        "location_id",
        "install_date",
        "condition_score",
        "source_type",
        "source_system",
        "data_version",
        "version",
        "is_deleted",
    },
    "work_orders": {
        "id",
        "facility_id",
        "priority",
        "due_at",
        "status",
        "idempotency_key",
        "source_type",
        "version",
        "is_deleted",
    },
    "inspection_tasks": {"id", "facility_id", "scheduled_at", "due_at", "status", "result_notes", "defer_reason"},
    "documents": {
        "id",
        "original_filename",
        "storage_key",
        "sha256",
        "status",
        "uploaded_by",
        "source_type",
        "version",
    },
    "document_parts": {"id", "document_id", "part_index", "text"},
    "document_chunks": {"id", "document_id", "chunk_index", "text", "token_count", "target_tokens", "overlap_tokens"},
    "agent_runs": {"id", "trace_id", "status", "started_at", "finished_at", "source_type", "version", "is_deleted"},
    "audit_logs": {"id", "agent_run_id", "tool_call_id", "action", "human_confirmation", "event_hash", "created_at"},
}
REQUIRED_INDEXES = {
    "facilities": {"uq_facilities_code", "idx_facilities_type_status", "idx_facilities_region_status"},
    "work_orders": {"uq_work_order_idempotency", "idx_work_order_status_due", "idx_work_order_facility_status"},
    "agent_runs": {"idx_agent_trace", "idx_agent_status_started"},
    "audit_logs": {"idx_audit_resource_time", "idx_audit_run", "idx_audit_tool"},
}
REQUIRED_FOREIGN_KEYS = {
    "fk_facility_location",
    "fk_report_facility",
    "fk_order_report",
    "fk_order_facility",
    "fk_order_technician",
    "fk_order_vendor",
    "fk_tool_call_run",
    "fk_audit_run",
}


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
    }


def verify_schema(url: str, allow_missing_audit_triggers: bool = False) -> dict[str, object]:
    connection = pymysql.connect(**_connection_args(url))
    try:
        with connection.cursor() as cursor:
            database = _connection_args(url)["database"]
            cursor.execute("SELECT TABLE_NAME FROM information_schema.tables WHERE table_schema=%s", (database,))
            tables = {row["TABLE_NAME"] for row in cursor.fetchall()}
            errors: list[str] = []
            missing_tables = sorted(REQUIRED_TABLES - tables)
            if missing_tables:
                errors.append(f"missing_tables:{','.join(missing_tables)}")
            for table, required in REQUIRED_COLUMNS.items():
                cursor.execute(
                    "SELECT COLUMN_NAME FROM information_schema.columns WHERE table_schema=%s AND table_name=%s",
                    (database, table),
                )
                columns = {row["COLUMN_NAME"] for row in cursor.fetchall()}
                missing = sorted(required - columns)
                if missing:
                    errors.append(f"{table}.missing_columns:{','.join(missing)}")
            for table, required in REQUIRED_INDEXES.items():
                cursor.execute(
                    "SELECT DISTINCT INDEX_NAME FROM information_schema.statistics WHERE table_schema=%s AND table_name=%s",
                    (database, table),
                )
                indexes = {row["INDEX_NAME"] for row in cursor.fetchall()}
                missing = sorted(required - indexes)
                if missing:
                    errors.append(f"{table}.missing_indexes:{','.join(missing)}")
            cursor.execute(
                "SELECT CONSTRAINT_NAME FROM information_schema.REFERENTIAL_CONSTRAINTS WHERE CONSTRAINT_SCHEMA=%s",
                (database,),
            )
            foreign_keys = {row["CONSTRAINT_NAME"] for row in cursor.fetchall()}
            missing_foreign_keys = sorted(REQUIRED_FOREIGN_KEYS - foreign_keys)
            if missing_foreign_keys:
                errors.append(f"missing_foreign_keys:{','.join(missing_foreign_keys)}")
            cursor.execute("SELECT TRIGGER_NAME FROM information_schema.triggers WHERE TRIGGER_SCHEMA=%s", (database,))
            triggers = {row["TRIGGER_NAME"] for row in cursor.fetchall()}
            missing_triggers = sorted({"trg_audit_logs_no_update", "trg_audit_logs_no_delete"} - triggers)
            if missing_triggers and not allow_missing_audit_triggers:
                errors.append(f"missing_audit_triggers:{','.join(missing_triggers)}")
            return {
                "database": database,
                "tables": sorted(tables & REQUIRED_TABLES),
                "foreign_keys": sorted(REQUIRED_FOREIGN_KEYS & foreign_keys),
                "audit_triggers": sorted({"trg_audit_logs_no_update", "trg_audit_logs_no_delete"} & triggers),
                "missing_audit_triggers": missing_triggers,
                "errors": errors,
                "passed": not errors,
            }
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the Step 8 MySQL schema")
    parser.add_argument(
        "--url", default=os.getenv("MYSQL_URL", "mysql+pymysql://municipal:municipal_dev@127.0.0.1:3306/municipal_ops")
    )
    parser.add_argument("--allow-missing-audit-triggers", action="store_true")
    args = parser.parse_args()
    report = verify_schema(args.url, args.allow_missing_audit_triggers)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
