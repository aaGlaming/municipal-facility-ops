import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen


def download_file(url: str, destination: Path, timeout: int = 30, overwrite: bool = False) -> dict[str, object]:
    if destination.exists() and not overwrite:
        payload = destination.read_bytes()
        return {
            "url": url,
            "path": str(destination),
            "skipped_existing": True,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": "municipal-facility-ops/0.1"})
    with urlopen(request, timeout=timeout) as response:
        payload = response.read()
    destination.write_bytes(payload)
    return {
        "url": url,
        "path": str(destination),
        "retrieved_at": datetime.now(UTC).isoformat(),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def write_manifest(entries: dict[str, dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"generated_at": datetime.now(UTC).isoformat(), "files": entries}, indent=2), encoding="utf-8"
    )


def verify_manifest(path: Path) -> dict[str, object]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    checked = 0
    mismatches: list[str] = []
    root = path.parent.parent.parent
    for name, entry in manifest.get("files", {}).items():
        file_path = root / entry["path"]
        checked += 1
        if not file_path.exists():
            mismatches.append(f"{name}:missing")
            continue
        payload = file_path.read_bytes()
        if entry.get("bytes") is not None and entry["bytes"] != len(payload):
            mismatches.append(f"{name}:bytes")
        if entry.get("sha256") and entry["sha256"] != hashlib.sha256(payload).hexdigest():
            mismatches.append(f"{name}:sha256")
        if entry.get("rows") is not None and file_path.suffix.lower() == ".csv":
            with file_path.open(newline="", encoding="utf-8-sig") as stream:
                rows = sum(1 for _ in csv.DictReader(stream))
            if entry["rows"] != rows:
                mismatches.append(f"{name}:rows")
    return {"checked": checked, "mismatches": mismatches}


if __name__ == "__main__":
    print("已有公开数据保留不变；请通过 download_file(url, destination) 增量登记来源。")
