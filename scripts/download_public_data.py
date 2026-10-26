import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen


def download_file(url: str, destination: Path, timeout: int = 30) -> dict[str, object]:
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
    path.write_text(json.dumps({"generated_at": datetime.now(UTC).isoformat(), "files": entries}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    print("已有公开数据保留不变；请通过 download_file(url, destination) 增量登记来源。")
