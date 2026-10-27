"""Repeatable offline evaluator for the Step21 triage Gold Set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.agents.triage_agent import classify_issue
from app.schemas.triage import TriageRequest


def evaluate(path: Path) -> dict[str, float | int]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    category_hits = 0
    priority_hits = 0
    for row in rows:
        category, _, priority = classify_issue(TriageRequest(description=row["description"], region=row["region"]))
        category_hits += category == row["expected_category"]
        priority_hits += priority == row["expected_priority"]
    total = len(rows)
    return {
        "total": total,
        "category_accuracy": round(category_hits / total, 4) if total else 0.0,
        "priority_accuracy": round(priority_hits / total, 4) if total else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="evaluation/datasets/triage_gold.jsonl")
    args = parser.parse_args()
    print(json.dumps(evaluate(Path(args.path)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
