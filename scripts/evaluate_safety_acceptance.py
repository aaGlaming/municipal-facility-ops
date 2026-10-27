"""Repeatable offline evaluator for Step23 safety and acceptance rules."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.agents.safety_acceptance_agent import SafetyAgent
from app.schemas.safety_acceptance import SafetyAssessmentRequest


def evaluate(path: Path) -> dict[str, float | int]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    risk_hits = 0
    confirmation_hits = 0
    for row in rows:
        result = SafetyAgent().assess(
            SafetyAssessmentRequest(
                facility_type=row["facility_type"],
                issue_type=row["issue_type"],
                work_description=row["work_description"],
                region=row["region"],
                live_power=row.get("live_power", False),
                road_closure=row.get("road_closure", False),
                high_work=row.get("high_work", False),
            )
        )
        risk_hits += result.risk_level == row["expected_risk"]
        confirmation_hits += result.requires_confirmation == row["expected_confirmation"]
    total = len(rows)
    return {
        "total": total,
        "risk_accuracy": round(risk_hits / total, 4) if total else 0.0,
        "confirmation_accuracy": round(confirmation_hits / total, 4) if total else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="evaluation/datasets/safety_acceptance_gold.jsonl")
    args = parser.parse_args()
    print(json.dumps(evaluate(Path(args.path)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
