import argparse
import csv
import hashlib
import io
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

GENERATOR_VERSION = "synthetic-v2"
GENERATED_AT = "2026-01-01T00:00:00Z"
FACILITY_TYPES = [
    "street_light",
    "traffic_signal",
    "road_surface",
    "manhole",
    "sidewalk",
    "drainage",
    "waste_bin",
    "green_space",
]
PRIORITIES = ["P1", "P2", "P3", "P4"]
WORK_ORDER_STATUSES = [
    "NEW",
    "TRIAGED",
    "ASSIGNED",
    "IN_PROGRESS",
    "WAITING_CONFIRMATION",
    "COMPLETED",
    "ACCEPTED",
    "CLOSED",
]
AGENT_NAMES = ["triage", "facility", "sla", "inspection", "dispatch", "safety", "acceptance"]
SKILLS = ["electrical", "traffic", "road", "civil", "drainage", "waste", "greenery"]


def _metadata() -> dict[str, str]:
    return {"source_type": "synthetic", "generator_version": GENERATOR_VERSION, "generated_at": GENERATED_AT}


def _iso_date(day: int) -> str:
    return (datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=day)).date().isoformat()


def _iso_datetime(day: int, hour: int = 0) -> str:
    return (datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=day, hours=hour)).isoformat().replace("+00:00", "Z")


def _csv_content(headers: list[str], rows: list[dict[str, object]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _write(output_dir: Path, filename: str, content: str) -> None:
    with (output_dir / filename).open("w", encoding="utf-8", newline="") as stream:
        stream.write(content)


def _positive(name: str, value: int) -> int:
    if value < 1:
        raise ValueError(f"{name} must be positive")
    return value


def generate_synthetic_data(
    output_dir: Path,
    seed: int = 20261025,
    facility_count: int = 500,
    report_count: int = 1200,
    inspection_count: int = 1600,
    work_order_count: int = 1800,
    acceptance_count: int = 900,
    agent_run_count: int = 1200,
    audit_count: int = 1800,
    team_count: int = 20,
    technician_count: int = 100,
    vendor_count: int = 40,
) -> dict[str, str]:
    counts = {
        "facility_count": facility_count,
        "report_count": report_count,
        "inspection_count": inspection_count,
        "work_order_count": work_order_count,
        "acceptance_count": acceptance_count,
        "agent_run_count": agent_run_count,
        "audit_count": audit_count,
        "team_count": team_count,
        "technician_count": technician_count,
        "vendor_count": vendor_count,
    }
    for name, value in counts.items():
        _positive(name, value)

    rng = random.Random(seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = _metadata()
    generated: dict[str, str] = {}

    facilities: list[dict[str, object]] = []
    locations: list[dict[str, object]] = []
    for index in range(1, facility_count + 1):
        facility_id = f"FAC-{index:05d}"
        facility_type = FACILITY_TYPES[(index - 1) % len(FACILITY_TYPES)]
        district = f"DISTRICT-{((index - 1) % 12) + 1:02d}"
        latitude = round(40.70 + rng.random() * 0.24, 6)
        longitude = round(-74.05 + rng.random() * 0.24, 6)
        facilities.append(
            {
                "facility_id": facility_id,
                "facility_code": f"MUNI-{facility_type.upper()}-{index:05d}",
                "facility_type": facility_type,
                "facility_name": f"Synthetic {facility_type.replace('_', ' ').title()} {index:05d}",
                "borough": district,
                "address": f"{100 + index} Municipal Avenue",
                "latitude": latitude,
                "longitude": longitude,
                "install_date": _iso_date(-rng.randint(365, 3650)),
                "condition_score": rng.randint(45, 98),
                "criticality": "critical" if facility_type in {"traffic_signal", "drainage"} else "normal",
                **metadata,
            }
        )
        locations.append(
            {
                "location_id": f"LOC-{index:05d}",
                "facility_id": facility_id,
                "address": facilities[-1]["address"],
                "district": district,
                "latitude": latitude,
                "longitude": longitude,
                **metadata,
            }
        )

    teams = [
        {
            "team_id": f"TEAM-{index:03d}",
            "team_name": f"Municipal Team {index:03d}",
            "district": f"DISTRICT-{((index - 1) % 12) + 1:02d}",
            "primary_skill": SKILLS[(index - 1) % len(SKILLS)],
            "max_daily_tasks": 6 + (index % 5),
            "active": "true",
            **metadata,
        }
        for index in range(1, team_count + 1)
    ]
    technicians = [
        {
            "technician_id": f"TECH-{index:04d}",
            "technician_name": f"Technician {index:04d}",
            "team_id": teams[(index - 1) % len(teams)]["team_id"],
            "primary_skill": SKILLS[(index - 1) % len(SKILLS)],
            "max_daily_tasks": 4 + (index % 5),
            "active": "true" if index % 13 else "false",
            **metadata,
        }
        for index in range(1, technician_count + 1)
    ]
    vendors = [
        {
            "vendor_id": f"VEN-{index:04d}",
            "vendor_name": f"Municipal Service Vendor {index:04d}",
            "service_scope": FACILITY_TYPES[(index - 1) % len(FACILITY_TYPES)],
            "rating": round(3.0 + rng.random() * 2.0, 2),
            "contact_phone": f"+1-212-555-{index:04d}",
            "active": "true" if index % 11 else "false",
            **metadata,
        }
        for index in range(1, vendor_count + 1)
    ]
    sla_rules = [
        {
            "sla_rule_id": f"SLA-{facility_type.upper()}-{priority}",
            "facility_type": facility_type,
            "priority": priority,
            "first_response_hours": {"P1": 1, "P2": 4, "P3": 24, "P4": 72}[priority],
            "resolution_hours": {"P1": 4, "P2": 24, "P3": 72, "P4": 168}[priority],
            "escalation_after_hours": {"P1": 2, "P2": 12, "P3": 48, "P4": 120}[priority],
            **metadata,
        }
        for facility_type in FACILITY_TYPES
        for priority in PRIORITIES
    ]

    reports = []
    for index in range(1, report_count + 1):
        facility = facilities[(index - 1) % len(facilities)]
        reports.append(
            {
                "report_id": f"RPT-{index:06d}",
                "facility_id": facility["facility_id"],
                "reported_at": _iso_datetime(index % 270, index % 24),
                "category": facility["facility_type"],
                "description": f"Synthetic resident report for {facility['facility_type']}.",
                "channel": ["web", "phone", "mobile", "inspection"][(index - 1) % 4],
                "status": ["new", "triaged", "assigned", "closed"][(index - 1) % 4],
                **metadata,
            }
        )

    inspections = []
    for index in range(1, inspection_count + 1):
        facility = facilities[(index - 1) % len(facilities)]
        technician = technicians[(index - 1) % len(technicians)]
        inspections.append(
            {
                "inspection_id": f"INS-{index:06d}",
                "facility_id": facility["facility_id"],
                "inspector_id": technician["technician_id"],
                "scheduled_at": _iso_datetime(index % 270),
                "completed_at": _iso_datetime(index % 270, 8),
                "result": ["pass", "minor_defect", "major_defect"][(index - 1) % 3],
                "severity": ["low", "medium", "critical"][(index - 1) % 3],
                "notes": f"Synthetic inspection result for {facility['facility_type']}.",
                **metadata,
            }
        )

    work_orders = []
    for index in range(1, work_order_count + 1):
        report = reports[(index - 1) % len(reports)]
        facility = facilities[(index - 1) % len(facilities)]
        technician = technicians[(index - 1) % len(technicians)]
        vendor = vendors[(index - 1) % len(vendors)]
        work_orders.append(
            {
                "work_order_id": f"WO-{index:06d}",
                "facility_id": facility["facility_id"],
                "report_id": report["report_id"],
                "assigned_technician_id": technician["technician_id"],
                "vendor_id": vendor["vendor_id"],
                "created_at": _iso_datetime(index % 270),
                "due_at": _iso_datetime((index % 270) + 1, 8),
                "completed_at": _iso_datetime((index % 270) + 1, 16) if index % 4 else "",
                "priority": PRIORITIES[(index - 1) % len(PRIORITIES)],
                "status": WORK_ORDER_STATUSES[(index - 1) % len(WORK_ORDER_STATUSES)],
                "problem_type": facility["facility_type"],
                "planned_action": ["inspect", "repair", "replace_component", "monitor"][(index - 1) % 4],
                "idempotency_key": f"wo-{index:06d}-synthetic-v2",
                **metadata,
            }
        )

    acceptances = [
        {
            "acceptance_id": f"ACC-{index:06d}",
            "work_order_id": work_orders[(index - 1) % len(work_orders)]["work_order_id"],
            "reviewer_id": technicians[(index - 1) % len(technicians)]["technician_id"],
            "accepted_at": _iso_datetime((index % 270) + 2, 10),
            "result": ["accepted", "conditional_acceptance", "rework_required"][(index - 1) % 3],
            "evidence_uri": f"/uploads/evidence/WO-{((index - 1) % len(work_orders)) + 1:06d}.json",
            "comments": "Synthetic acceptance record.",
            **metadata,
        }
        for index in range(1, acceptance_count + 1)
    ]
    agent_runs = [
        {
            "run_id": f"RUN-{index:06d}",
            "agent_name": AGENT_NAMES[(index - 1) % len(AGENT_NAMES)],
            "input_type": ["citizen_report", "inspection", "work_order"][(index - 1) % 3],
            "status": ["completed", "waiting_confirmation", "failed"][(index - 1) % 3],
            "iterations": 1 + (index % 4),
            "input_tokens": 400 + (index % 700),
            "output_tokens": 80 + (index % 220),
            "started_at": _iso_datetime(index % 270),
            "finished_at": _iso_datetime(index % 270, 0 if index % 3 else 1),
            **metadata,
        }
        for index in range(1, agent_run_count + 1)
    ]
    audit_logs = [
        {
            "audit_id": f"AUD-{index:06d}",
            "run_id": agent_runs[(index - 1) % len(agent_runs)]["run_id"],
            "actor": ["supervisor", "dispatcher", "technician", "auditor"][(index - 1) % 4],
            "action": ["triage", "assign", "status_change", "acceptance"][(index - 1) % 4],
            "target_type": ["report", "work_order", "inspection", "acceptance"][(index - 1) % 4],
            "target_id": work_orders[(index - 1) % len(work_orders)]["work_order_id"],
            "result": ["allowed", "denied", "waiting_confirmation"][(index - 1) % 3],
            "detail": json.dumps({"synthetic": True, "generator_version": GENERATOR_VERSION}, ensure_ascii=False),
            "created_at": _iso_datetime(index % 270),
            **metadata,
        }
        for index in range(1, audit_count + 1)
    ]
    knowledge_docs = [
        ("street_light", "路灯故障巡检 SOP", "路灯报修应先确认设施编号、道路位置和是否存在裸露导线。"),
        ("traffic_signal", "交通信号故障处置 SOP", "交通信号灯故障应按路口重要性和是否影响通行判断优先级。"),
        ("road_surface", "道路破损维修规范", "道路破损应记录位置、影响范围和现场安全措施，再安排维修。"),
        ("manhole", "井盖缺失应急规范", "井盖缺失涉及坠落风险时，应先设置围挡和警示，再安排抢修。"),
        ("sidewalk", "人行道巡检规范", "人行道高差和破损应记录影响通行的范围并核对无障碍要求。"),
        ("drainage", "排水设施巡检规范", "积水和排水堵塞应记录天气、积水范围和周边交通影响。"),
        ("waste_bin", "垃圾设施维护规范", "垃圾设施溢满或破损应记录容量、清运状态和周边卫生影响。"),
    ]
    knowledge_content = (
        "\n".join(
            json.dumps(
                {
                    "document_id": f"SYN-DOC-{index:03d}",
                    "title": title,
                    "facility_type": facility_type,
                    "content": content,
                    "effective_date": "2026-01-01",
                    "version": "synthetic-2.0",
                    "authority": "demo-only",
                    **metadata,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            for index, (facility_type, title, content) in enumerate(knowledge_docs, start=1)
        )
        + "\n"
    )

    datasets: list[tuple[str, list[str], list[dict[str, object]]]] = [
        ("synthetic_facilities.csv", list(facilities[0]), facilities),
        ("synthetic_locations.csv", list(locations[0]), locations),
        ("synthetic_teams.csv", list(teams[0]), teams),
        ("synthetic_technicians.csv", list(technicians[0]), technicians),
        ("synthetic_vendors.csv", list(vendors[0]), vendors),
        ("synthetic_sla_rules.csv", list(sla_rules[0]), sla_rules),
        ("synthetic_citizen_reports.csv", list(reports[0]), reports),
        ("synthetic_inspection_tasks.csv", list(inspections[0]), inspections),
        ("synthetic_work_orders.csv", list(work_orders[0]), work_orders),
        ("synthetic_acceptance_records.csv", list(acceptances[0]), acceptances),
        ("synthetic_agent_runs.csv", list(agent_runs[0]), agent_runs),
        ("synthetic_audit_logs.csv", list(audit_logs[0]), audit_logs),
    ]
    for filename, headers, rows in datasets:
        content = _csv_content(headers, rows)
        _write(output_dir, filename, content)
        generated[filename] = content
    _write(output_dir, "synthetic_knowledge_docs.jsonl", knowledge_content)
    generated["synthetic_knowledge_docs.jsonl"] = knowledge_content
    return generated


def register_synthetic_manifest(
    output_dir: Path, manifest_path: Path, seed: int = 20261025
) -> dict[str, dict[str, object]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"files": {}}
    project_root = manifest_path.parent.parent.parent
    entries: dict[str, dict[str, object]] = {}
    for file_path in sorted(output_dir.glob("synthetic_*")):
        payload = file_path.read_bytes()
        relative = file_path.resolve().relative_to(project_root.resolve()).as_posix()
        name = file_path.stem
        existing = manifest.get("files", {}).get(name, {})
        entry = {
            **existing,
            "name": name,
            "kind": "synthetic",
            "path": relative,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "generator_version": GENERATOR_VERSION,
            "seed": seed,
            "generated_at": GENERATED_AT,
        }
        if file_path.suffix.lower() == ".csv":
            with file_path.open(newline="", encoding="utf-8") as stream:
                entry["rows"] = sum(1 for _ in csv.DictReader(stream))
        elif file_path.suffix.lower() == ".jsonl":
            entry["rows"] = sum(1 for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip())
        manifest.setdefault("files", {})[name] = entry
        entries[name] = entry
    manifest["generated_at"] = GENERATED_AT
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic synthetic municipal operations data")
    parser.add_argument("--output-dir", type=Path, default=Path("data/synthetic"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/manifest.json"))
    parser.add_argument("--seed", type=int, default=20261025)
    args = parser.parse_args()
    generate_synthetic_data(args.output_dir, seed=args.seed)
    register_synthetic_manifest(args.output_dir, args.manifest, seed=args.seed)
    print(f"generated synthetic data in {args.output_dir} with seed={args.seed}")


if __name__ == "__main__":
    main()
