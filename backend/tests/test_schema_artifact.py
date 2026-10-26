from pathlib import Path


def test_step8_schema_declares_business_tables_and_integrity_controls() -> None:
    schema = Path("infra/mysql/init/001_schema.sql").read_text(encoding="utf-8").lower()
    required_tables = {
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
        "agent_runs",
        "tool_calls",
        "audit_logs",
    }
    assert all(f"create table if not exists {table}" in schema for table in required_tables)
    assert "unique key uq_work_order_idempotency" in schema
    assert "foreign key (facility_id) references facilities(id) on delete restrict" in schema
    assert "create trigger trg_audit_logs_no_update" in schema
    assert "create trigger trg_audit_logs_no_delete" in schema
    assert "is_deleted boolean not null default false" in schema
    assert "source_type varchar(32) not null" in schema
    assert "data_version varchar(64) not null" in schema


def test_step8_permission_template_has_no_real_secret_and_is_least_privilege() -> None:
    template = Path("infra/mysql/security/001_app_role.sql.template").read_text(encoding="utf-8").lower()
    assert "replace_with_secret" in template
    assert "grant select, insert, update, delete" in template
    assert "grant all privileges" not in template
