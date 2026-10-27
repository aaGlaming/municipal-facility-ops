"""Create and independently verify the Step34 project backup."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKUP_ITEMS = (
    "data",
    "evaluation",
    "infra",
    "backend/.env.example",
    "frontend/.env.example",
    "compose.yaml",
    "README.md",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _files(source: Path) -> list[Path]:
    return [source] if source.is_file() else sorted(path for path in source.rglob("*") if path.is_file())


def _copy_payload(target: Path) -> list[dict[str, Any]]:
    payload = target / "payload"
    payload.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, Any]] = []
    for item in BACKUP_ITEMS:
        source = ROOT / item
        if not source.exists():
            continue
        for file in _files(source):
            relative = file.relative_to(ROOT)
            if relative.as_posix() == "evaluation/reports/step34-backup-restore.json":
                continue
            destination = payload / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, destination)
            manifest.append(
                {"path": str(relative).replace("\\", "/"), "size": file.stat().st_size, "sha256": _sha256(file)}
            )
    return manifest


def _verify_restore(target: Path, manifest: list[dict[str, Any]]) -> list[str]:
    restore = target / "restore-check"
    if restore.exists():
        shutil.rmtree(restore)
    shutil.copytree(target / "payload", restore)
    mismatches: list[str] = []
    for item in manifest:
        file = restore / item["path"]
        if not file.exists() or file.stat().st_size != item["size"] or _sha256(file) != item["sha256"]:
            mismatches.append(item["path"])
    return mismatches


def _mysql_status() -> dict[str, Any]:
    try:
        with socket.create_connection(("127.0.0.1", 3306), timeout=1):
            return {
                "status": "reachable",
                "dump": "not_run",
                "reason": "mysqldump requires an explicit configured credential",
            }
    except OSError:
        return {
            "status": "unavailable",
            "dump": "not_run",
            "reason": "MySQL is not running locally; schema and seed artifacts are included",
        }


def run(output: Path) -> dict[str, Any]:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    manifest = _copy_payload(output)
    (output / "manifest.json").write_text(
        json.dumps({"created_at": datetime.now(UTC).isoformat(), "files": manifest}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    mismatches = _verify_restore(output, manifest)
    critical = [
        "data/manifests/manifest.json",
        "data/processed/facility_issue_events.csv",
        "data/synthetic/synthetic_facilities.csv",
        "data/chroma/chroma.sqlite3",
        "evaluation/benchmark_config.json",
        "evaluation/reports/step30-rag-baseline.json",
        "evaluation/reports/step31-agent-security.json",
        "infra/mysql/init/001_schema.sql",
        "backend/.env.example",
    ]
    restore = output / "restore-check"
    missing = [item for item in critical if not (restore / item).exists()]
    return {
        "backup_version": "step34-v1",
        "output": str(output),
        "file_count": len(manifest),
        "bytes": sum(item["size"] for item in manifest),
        "sha256_manifest": str(output / "manifest.json"),
        "restore": {
            "directory": str(restore),
            "mismatches": mismatches,
            "missing_critical": missing,
            "passed": not mismatches and not missing,
        },
        "mysql": _mysql_status(),
        "secrets_excluded": ["backend/.env", "frontend/.env"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="../backups/municipal-facility-ops/step34")
    parser.add_argument("--report", default="evaluation/reports/step34-backup-restore.json")
    args = parser.parse_args()
    result = run((ROOT / args.output).resolve())
    report = ROOT / args.report
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["restore"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
