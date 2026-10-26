import csv
import io
import random
from datetime import UTC, datetime
from pathlib import Path

GENERATOR_VERSION = "synthetic-v1"


def _csv_text(headers: list[str], rows: list[dict[str, object]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def generate_synthetic_data(output_dir: Path, seed: int = 20261025, facility_count: int = 500) -> dict[str, str]:
    rng = random.Random(seed)
    # 固定生成时间，确保相同 seed 的输出可直接比较和复现。
    generated_at = datetime(2026, 1, 1, tzinfo=UTC).isoformat().replace("+00:00", "Z")
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    types = ["street_light", "traffic_signal", "road_surface", "manhole", "waste_bin", "green_space"]
    for index in range(1, facility_count + 1):
        rows.append(
            {
                "facility_id": f"FAC-{index:05d}",
                "facility_type": types[(index - 1) % len(types)],
                "facility_name": f"Synthetic Facility {index:05d}",
                "borough": f"DISTRICT-{rng.randint(1, 12):02d}",
                "source_type": "synthetic",
                "generator_version": GENERATOR_VERSION,
                "generated_at": generated_at,
            }
        )
    headers = list(rows[0])
    content = _csv_text(headers, rows)
    (output_dir / "synthetic_facilities.csv").write_text(content, encoding="utf-8")
    return {"synthetic_facilities.csv": content}


if __name__ == "__main__":
    generate_synthetic_data(Path("data/synthetic"))
