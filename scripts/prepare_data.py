import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MAPPING_VERSION = "public-events-v2"
HEADERS = [
    "event_id",
    "source_dataset",
    "source_type",
    "category",
    "subcategory",
    "description",
    "status",
    "created_at",
    "closed_at",
    "agency",
    "address",
    "borough",
    "latitude",
    "longitude",
    "external_id",
    "source_row_number",
    "mapping_version",
    "cleaning_batch_id",
]
BOROUGH_MAP = {
    "B": "BROOKLYN",
    "BK": "BROOKLYN",
    "BROOKLYN": "BROOKLYN",
    "K": "BROOKLYN",
    "BX": "BRONX",
    "X": "BRONX",
    "BRONX": "BRONX",
    "M": "MANHATTAN",
    "MN": "MANHATTAN",
    "MANHATTAN": "MANHATTAN",
    "Q": "QUEENS",
    "QN": "QUEENS",
    "QUEENS": "QUEENS",
    "R": "STATEN ISLAND",
    "S": "STATEN ISLAND",
    "SI": "STATEN ISLAND",
    "STATEN ISLAND": "STATEN ISLAND",
    "RICHMOND": "STATEN ISLAND",
}


def _text(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = (row.get(key) or "").strip()
        if value:
            return value
    return ""


def _normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_borough(value: str) -> str:
    normalized = _normalize_spaces(value).upper()
    return BOROUGH_MAP.get(normalized, normalized)


def _normalize_category(row: dict[str, str], source_name: str) -> tuple[str, str]:
    raw_category = _text(row, "complaint_type", "facility_type", "category")
    raw_subcategory = _text(row, "descriptor", "descriptor_2", "subcategory")
    combined = f"{raw_category} {raw_subcategory}".lower()
    if "street light" in combined or "streetlight" in combined:
        return "street_light", raw_subcategory
    if "traffic signal" in combined or "signal" in combined:
        return "traffic_signal", raw_subcategory
    if "pothole" in combined or "street condition" in combined or "road" in combined or "pavement" in combined:
        return "road_surface", raw_subcategory or "pothole"
    if "pothole" in source_name:
        return "road_surface", raw_subcategory or "pothole"
    return (raw_category.lower().replace(" ", "_") or "unknown"), raw_subcategory


def _normalize_status(value: str, source_name: str) -> str:
    if not value and "pothole" in source_name:
        return "closed"
    return _normalize_spaces(value).lower().replace(" ", "_") or "unknown"


def _parse_datetime(value: str, failures: list[dict[str, Any]], dataset: str, row_number: int, field: str) -> str:
    value = value.strip()
    if not value:
        return ""
    candidate = value.replace("Z", "+00:00")
    parsed: datetime | None = None
    for parser in (
        lambda: datetime.fromisoformat(candidate),
        lambda: datetime.strptime(value, "%Y/%m/%d %H:%M:%S"),
        lambda: datetime.strptime(value, "%Y-%m-%d %H:%M:%S"),
        lambda: datetime.strptime(value, "%Y-%m-%d"),
    ):
        try:
            parsed = parser()
            break
        except ValueError:
            continue
    if parsed is None:
        failures.append(
            {
                "source_dataset": dataset,
                "source_row_number": row_number,
                "field": field,
                "value": value,
                "reason": "invalid_datetime",
            }
        )
        return ""
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _normalize_coordinate(
    value: str,
    minimum: float,
    maximum: float,
    field: str,
    failures: list[dict[str, Any]],
    dataset: str,
    row_number: int,
) -> str:
    value = value.strip()
    if not value:
        return ""
    try:
        number = float(value)
    except ValueError:
        failures.append(
            {
                "source_dataset": dataset,
                "source_row_number": row_number,
                "field": field,
                "value": value,
                "reason": "invalid_coordinate",
            }
        )
        return ""
    if not minimum <= number <= maximum:
        failures.append(
            {
                "source_dataset": dataset,
                "source_row_number": row_number,
                "field": field,
                "value": value,
                "reason": "coordinate_out_of_range",
            }
        )
        return ""
    return f"{number:.7f}".rstrip("0").rstrip(".")


def _address(row: dict[str, str], source_name: str) -> str:
    if "pothole" in source_name:
        return _normalize_spaces(f"{_text(row, 'housenum')} {_text(row, 'onfacename', 'onprimname')}")
    return _normalize_spaces(_text(row, "incident_address", "address", "street_name", "landmark"))


def _external_id(row: dict[str, str], source_row_number: int) -> str:
    return _text(row, "unique_key", "Unique Key", "defnum", "external_id") or f"row-{source_row_number}"


def _agency(row: dict[str, str], source_name: str) -> str:
    return "NYC Department of Transportation" if "pothole" in source_name else _text(row, "agency_name", "agency")


def _description(row: dict[str, str], source_name: str) -> str:
    if "pothole" in source_name:
        parts = [_text(row, "source"), _text(row, "onfacename"), "pothole work order"]
    else:
        parts = [
            _text(row, "complaint_type", "category"),
            _text(row, "descriptor", "subcategory"),
            _text(row, "descriptor_2"),
            _text(row, "resolution_description", "description"),
        ]
    return _normalize_spaces(" ".join(filter(None, parts)))


def _source_times(row: dict[str, str], source_name: str) -> tuple[str, str]:
    return (
        (_text(row, "rptdate"), _text(row, "rptclosed"))
        if "pothole" in source_name
        else (_text(row, "created_date", "created_at"), _text(row, "closed_date", "closed_at"))
    )


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _field_reports(rows: list[dict[str, str]]) -> tuple[dict[str, Any], dict[str, int]]:
    statistics: dict[str, Any] = {}
    missing: dict[str, int] = {}
    for field in HEADERS:
        values = [row.get(field, "") for row in rows]
        missing_count = sum(not value for value in values)
        missing[field] = missing_count
        statistics[field] = {
            "row_count": len(values),
            "non_empty": len(values) - missing_count,
            "missing": missing_count,
            "unique_count": len({value for value in values if value}),
        }
    return statistics, missing


def prepare_events(
    input_files: list[Path],
    output_file: Path,
    report_dir: Path | None = None,
    batch_id: str | None = None,
    manifest_path: Path | None = None,
) -> dict[str, object]:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    report_dir = report_dir or output_file.parent
    report_dir.mkdir(parents=True, exist_ok=True)
    batch_id = batch_id or datetime.now(UTC).strftime("batch-%Y%m%dT%H%M%SZ")
    rows: list[dict[str, str]] = []
    failures: list[dict[str, Any]] = []
    source_reports: list[dict[str, Any]] = []
    external_id_counts: dict[str, Counter[str]] = defaultdict(Counter)
    event_id_counts: Counter[str] = Counter()
    for input_file in sorted(input_files):
        source_dataset = input_file.stem
        source_rows = 0
        with input_file.open(newline="", encoding="utf-8-sig") as stream:
            for source_row_number, source in enumerate(csv.DictReader(stream), start=2):
                source_rows += 1
                external_id = _external_id(source, source_row_number)
                external_id_counts[source_dataset][external_id] += 1
                category, subcategory = _normalize_category(source, source_dataset)
                raw_created, raw_closed = _source_times(source, source_dataset)
                created_at = _parse_datetime(raw_created, failures, source_dataset, source_row_number, "created_at")
                closed_at = _parse_datetime(raw_closed, failures, source_dataset, source_row_number, "closed_at")
                latitude = _normalize_coordinate(
                    _text(source, "latitude"), -90, 90, "latitude", failures, source_dataset, source_row_number
                )
                longitude = _normalize_coordinate(
                    _text(source, "longitude"), -180, 180, "longitude", failures, source_dataset, source_row_number
                )
                base_event_id = f"{source_dataset}-{external_id}"
                event_id_counts[base_event_id] += 1
                suffix = "" if event_id_counts[base_event_id] == 1 else f"-dup-{event_id_counts[base_event_id]}"
                rows.append(
                    {
                        "event_id": f"{base_event_id}{suffix}",
                        "source_dataset": source_dataset,
                        "source_type": "public",
                        "category": category,
                        "subcategory": subcategory,
                        "description": _description(source, source_dataset),
                        "status": _normalize_status(_text(source, "status"), source_dataset),
                        "created_at": created_at,
                        "closed_at": closed_at,
                        "agency": _agency(source, source_dataset),
                        "address": _address(source, source_dataset),
                        "borough": _normalize_borough(_text(source, "borough", "boro", "park_borough")),
                        "latitude": latitude,
                        "longitude": longitude,
                        "external_id": external_id,
                        "source_row_number": str(source_row_number),
                        "mapping_version": MAPPING_VERSION,
                        "cleaning_batch_id": batch_id,
                    }
                )
        source_reports.append(
            {
                "source_dataset": source_dataset,
                "path": input_file.as_posix(),
                "bytes": input_file.stat().st_size,
                "sha256": _file_sha256(input_file),
                "rows": source_rows,
            }
        )
    with output_file.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    summary_file = output_file.with_name("facility_issue_events_summary.json")
    _write_json(
        summary_file,
        {
            "generated_at": datetime.now(UTC).isoformat(),
            "output": output_file.as_posix(),
            "rows": len(rows),
            "source_counts": dict(Counter(row["source_dataset"] for row in rows)),
            "category_counts": dict(Counter(row["category"] for row in rows)),
            "sha256": _file_sha256(output_file),
            "fields": HEADERS,
        },
    )
    field_statistics, missing_values = _field_reports(rows)
    duplicate_external_ids = {
        dataset: dict(sorted(counts.items()))
        for dataset, counts in external_id_counts.items()
        if any(count > 1 for count in counts.values())
    }
    _write_json(report_dir / "field_statistics.json", {"batch_id": batch_id, "fields": field_statistics})
    _write_json(report_dir / "missing_values.json", {"batch_id": batch_id, "fields": missing_values})
    _write_json(
        report_dir / "duplicate_values.json",
        {
            "batch_id": batch_id,
            "duplicate_external_ids": duplicate_external_ids,
            "duplicate_event_ids": {key: count for key, count in event_id_counts.items() if count > 1},
        },
    )
    (report_dir / "cleaning_failures.jsonl").write_text(
        "".join(json.dumps(failure, ensure_ascii=False) + "\n" for failure in failures), encoding="utf-8"
    )
    generated_at = datetime.now(UTC).isoformat()
    batch_report: dict[str, Any] = {
        "batch_id": batch_id,
        "generated_at": generated_at,
        "mapping_version": MAPPING_VERSION,
        "input_files": source_reports,
        "output": {
            "path": output_file.as_posix(),
            "rows": len(rows),
            "bytes": output_file.stat().st_size,
            "sha256": _file_sha256(output_file),
        },
        "failed_values": len(failures),
        "failure_file": (report_dir / "cleaning_failures.jsonl").as_posix(),
        "filter": "none; all source rows retained",
    }
    _write_json(report_dir / "cleaning_batch.json", batch_report)
    if manifest_path:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"files": {}}
        files = manifest.setdefault("files", {})
        files["facility_issue_events"] = {
            **files.get("facility_issue_events", {}),
            "name": "facility_issue_events",
            "kind": "processed",
            "path": output_file.as_posix().replace("\\", "/"),
            "rows": len(rows),
            "bytes": output_file.stat().st_size,
            "sha256": _file_sha256(output_file),
            "batch_id": batch_id,
            "mapping_version": MAPPING_VERSION,
            "generated_at": generated_at,
        }
        files["facility_issue_events_summary"] = {
            **files.get("facility_issue_events_summary", {}),
            "name": "facility_issue_events_summary",
            "kind": "processed",
            "path": summary_file.as_posix().replace("\\", "/"),
            "bytes": summary_file.stat().st_size,
            "sha256": _file_sha256(summary_file),
            "batch_id": batch_id,
            "mapping_version": MAPPING_VERSION,
            "generated_at": generated_at,
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "rows": len(rows),
        "sha256": _file_sha256(output_file),
        "output": str(output_file),
        "batch_id": batch_id,
        "failed_values": len(failures),
        "reports": str(report_dir),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize public municipal issue data")
    parser.add_argument("--input-dir", type=Path, default=Path("data/raw/public"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    parser.add_argument("--manifest", type=Path, default=Path("data/manifests/manifest.json"))
    parser.add_argument("--batch-id", default=None)
    args = parser.parse_args()
    result = prepare_events(
        sorted(args.input_dir.glob("*.csv")),
        args.output_dir / "facility_issue_events.csv",
        report_dir=args.output_dir,
        batch_id=args.batch_id,
        manifest_path=args.manifest,
    )
    print(result)


if __name__ == "__main__":
    main()
