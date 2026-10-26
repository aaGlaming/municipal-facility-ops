import csv
import hashlib
from pathlib import Path

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
]


def prepare_events(input_files: list[Path], output_file: Path) -> dict[str, object]:
    rows: list[dict[str, str]] = []
    for input_file in input_files:
        with input_file.open(newline="", encoding="utf-8-sig") as stream:
            for index, source in enumerate(csv.DictReader(stream), start=1):
                external_id = (
                    source.get("unique_key") or source.get("Unique Key") or source.get("external_id") or str(index)
                )
                rows.append(
                    {
                        "event_id": f"{input_file.stem}-{external_id}",
                        "source_dataset": input_file.stem,
                        "source_type": "public",
                        "category": source.get("category") or source.get("complaint_type") or "unknown",
                        "subcategory": source.get("subcategory") or "",
                        "description": source.get("description") or "",
                        "status": source.get("status") or "unknown",
                        "created_at": source.get("created_at") or source.get("created_date") or "",
                        "closed_at": source.get("closed_at") or source.get("closed_date") or "",
                        "agency": source.get("agency") or "",
                        "address": source.get("address") or "",
                        "borough": source.get("borough") or "",
                        "latitude": source.get("latitude") or "",
                        "longitude": source.get("longitude") or "",
                        "external_id": external_id,
                    }
                )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    digest = hashlib.sha256(output_file.read_bytes()).hexdigest()
    return {"rows": len(rows), "sha256": digest, "output": str(output_file)}


if __name__ == "__main__":
    inputs = sorted(Path("data/raw/public").glob("*.csv"))
    print(prepare_events(inputs, Path("data/processed/facility_issue_events.csv")))
