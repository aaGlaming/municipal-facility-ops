"""Repeatable offline evaluator for Step22 SLA rules."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from app.agents.scheduling_agent import SchedulingAgent
from app.schemas.scheduling import SlaPlanRequest


def evaluate(path: Path) -> dict[str, float | int]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    priority_hits = 0
    sla_hits = 0
    for row in rows:
        result = SchedulingAgent().plan_sla(
            SlaPlanRequest(
                issue_type=row["issue_type"],
                priority=row["priority"],
                region=row["region"],
                reported_at=datetime.fromisoformat(row["reported_at"]),
                public_safety=row["public_safety"],
                repeated_report=row["repeated_report"],
            )
        )
        priority_hits += result.priority == row["expected_priority"]
        sla_hits += result.sla_minutes == row["expected_sla_minutes"]
    total = len(rows)
    return {
        "total": total,
        "priority_accuracy": round(priority_hits / total, 4) if total else 0.0,
        "sla_minutes_accuracy": round(sla_hits / total, 4) if total else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="evaluation/datasets/scheduling_gold.jsonl")
    args = parser.parse_args()
    print(json.dumps(evaluate(Path(args.path)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
