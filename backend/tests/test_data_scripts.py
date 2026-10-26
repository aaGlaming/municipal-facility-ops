import csv
import hashlib
import io
import json
from pathlib import Path

from scripts.backup_data import copy_tree_with_manifest
from scripts.download_public_data import verify_manifest
from scripts.generate_synthetic_data import generate_synthetic_data
from scripts.prepare_data import prepare_events


def test_synthetic_generation_marks_source_and_is_repeatable(tmp_path: Path) -> None:
    first = generate_synthetic_data(
        tmp_path / "first", seed=7, facility_count=6, report_count=12, inspection_count=8, work_order_count=10
    )
    second = generate_synthetic_data(
        tmp_path / "second", seed=7, facility_count=6, report_count=12, inspection_count=8, work_order_count=10
    )
    assert first == second
    assert "source_type" in first["synthetic_facilities.csv"]


def test_synthetic_generation_covers_business_closure_and_foreign_keys(tmp_path: Path) -> None:
    generated = generate_synthetic_data(
        tmp_path,
        seed=11,
        facility_count=8,
        report_count=16,
        inspection_count=12,
        work_order_count=14,
        acceptance_count=7,
        agent_run_count=9,
        audit_count=15,
    )
    expected_files = {
        "synthetic_facilities.csv",
        "synthetic_locations.csv",
        "synthetic_teams.csv",
        "synthetic_technicians.csv",
        "synthetic_vendors.csv",
        "synthetic_sla_rules.csv",
        "synthetic_citizen_reports.csv",
        "synthetic_inspection_tasks.csv",
        "synthetic_work_orders.csv",
        "synthetic_acceptance_records.csv",
        "synthetic_agent_runs.csv",
        "synthetic_audit_logs.csv",
        "synthetic_knowledge_docs.jsonl",
    }
    assert expected_files <= generated.keys()

    def read_csv(name: str) -> list[dict[str, str]]:
        return list(csv.DictReader(io.StringIO(generated[name])))

    facilities = read_csv("synthetic_facilities.csv")
    locations = read_csv("synthetic_locations.csv")
    reports = read_csv("synthetic_citizen_reports.csv")
    inspections = read_csv("synthetic_inspection_tasks.csv")
    orders = read_csv("synthetic_work_orders.csv")
    acceptances = read_csv("synthetic_acceptance_records.csv")
    runs = read_csv("synthetic_agent_runs.csv")
    audits = read_csv("synthetic_audit_logs.csv")
    facility_ids = {row["facility_id"] for row in facilities}
    report_ids = {row["report_id"] for row in reports}
    work_order_ids = {row["work_order_id"] for row in orders}
    run_ids = {row["run_id"] for row in runs}

    assert len(facility_ids) == len(facilities)
    assert {row["facility_id"] for row in locations} == facility_ids
    assert {row["facility_id"] for row in reports} <= facility_ids
    assert {row["facility_id"] for row in inspections} <= facility_ids
    assert {row["report_id"] for row in orders} <= report_ids
    assert {row["facility_id"] for row in orders} <= facility_ids
    assert {row["work_order_id"] for row in acceptances} <= work_order_ids
    assert {row["run_id"] for row in audits} <= run_ids

    for name, content in generated.items():
        if name.endswith(".csv"):
            rows = list(csv.DictReader(io.StringIO(content)))
            assert all(
                row["source_type"] == "synthetic"
                and row["generator_version"] == "synthetic-v2"
                and row["generated_at"] == "2026-01-01T00:00:00Z"
                for row in rows
            )
        else:
            docs = [json.loads(line) for line in content.splitlines()]
            assert all(
                doc["source_type"] == "synthetic"
                and doc["generator_version"] == "synthetic-v2"
                and doc["generated_at"] == "2026-01-01T00:00:00Z"
                for doc in docs
            )


def test_prepare_events_writes_unified_output(tmp_path: Path) -> None:
    raw = tmp_path / "raw.csv"
    raw.write_text("unique_key,category,status\nA,Street Light Condition,Open\n", encoding="utf-8")
    output = tmp_path / "processed.csv"
    result = prepare_events([raw], output)
    assert result["rows"] == 1
    assert output.read_text(encoding="utf-8").splitlines()[0].startswith("event_id,")


def test_prepare_events_normalizes_sources_and_writes_quality_reports(tmp_path: Path) -> None:
    three_one_one = tmp_path / "nyc_311_relevant.csv"
    three_one_one.write_text(
        "unique_key,created_date,closed_date,agency,agency_name,complaint_type,descriptor,descriptor_2,status,incident_address,borough,latitude,longitude\n"
        "X-1,2026-10-24T01:56:18.000,,DOT,Department of Transportation,Street Light Condition,Street Light Out,,Open,1 MAIN ST,MN,40.7,-73.9\n"
        "X-1,bad-date,,DOT,Department of Transportation,Traffic Signal Condition,Signal Out,,In Progress,2 MAIN ST,Q,999,-73.8\n",
        encoding="utf-8",
    )
    potholes = tmp_path / "nyc_pothole_work_orders_closed.csv"
    potholes.write_text(
        "defnum,rptdate,rptclosed,boro,housenum,onfacename,source\n"
        "D-1,2026/09/28 00:00:00,2026/09/29 00:00:00,B,100,ALBANY AV,CTZ\n",
        encoding="utf-8",
    )
    before_hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (three_one_one, potholes)}
    output = tmp_path / "processed" / "facility_issue_events.csv"
    report_dir = tmp_path / "processed"

    result = prepare_events([three_one_one, potholes], output, report_dir=report_dir, batch_id="batch-test")

    rows = list(csv.DictReader(output.open(newline="", encoding="utf-8")))
    assert result["rows"] == 3
    assert len({row["event_id"] for row in rows}) == 3
    assert rows[0]["category"] == "street_light"
    assert rows[0]["borough"] == "MANHATTAN"
    assert rows[0]["created_at"] == "2026-10-24T01:56:18Z"
    assert rows[1]["category"] == "traffic_signal"
    assert rows[1]["borough"] == "QUEENS"
    assert rows[1]["latitude"] == ""
    assert rows[2]["category"] == "road_surface"
    assert rows[2]["borough"] == "BROOKLYN"
    assert rows[2]["address"] == "100 ALBANY AV"
    assert rows[0]["cleaning_batch_id"] == "batch-test"

    duplicate_report = json.loads((report_dir / "duplicate_values.json").read_text(encoding="utf-8"))
    missing_report = json.loads((report_dir / "missing_values.json").read_text(encoding="utf-8"))
    batch_report = json.loads((report_dir / "cleaning_batch.json").read_text(encoding="utf-8"))
    failures = (report_dir / "cleaning_failures.jsonl").read_text(encoding="utf-8").splitlines()
    assert duplicate_report["duplicate_external_ids"] == {"nyc_311_relevant": {"X-1": 2}}
    assert missing_report["fields"]["closed_at"] == 2
    assert batch_report["batch_id"] == "batch-test"
    assert batch_report["failed_values"] >= 2
    assert len(failures) >= 2
    assert all(
        hashlib.sha256(path.read_bytes()).hexdigest() == before_hashes[path.name] for path in (three_one_one, potholes)
    )


def test_backup_records_hashes(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    (source / "a.txt").write_text("hello", encoding="utf-8")
    report = copy_tree_with_manifest(source, target)
    assert report["copied_files"] == 1
    assert report["mismatches"] == []


def test_public_manifest_matches_downloaded_files() -> None:
    report = verify_manifest(Path("data/manifests/manifest.json"))
    assert report["mismatches"] == []
