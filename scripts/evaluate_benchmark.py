"""Validate and run the deterministic Step29 evaluation baseline."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.agents.safety_acceptance_agent import SafetyAgent
from app.agents.triage_agent import classify_issue
from app.schemas.safety_acceptance import SafetyAssessmentRequest
from app.schemas.triage import TriageRequest
from app.services.work_order_service import WORK_ORDER_TRANSITIONS
from evaluate_safety_acceptance import evaluate as evaluate_safety
from evaluate_scheduling import evaluate as evaluate_scheduling
from evaluate_triage import evaluate as evaluate_triage

ROOT = Path(__file__).resolve().parents[1]


def _rows(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"dataset is empty or contains a non-object row: {path}")
    ids = [row.get("id") for row in rows]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        raise ValueError(f"dataset IDs must be unique and non-empty: {path}")
    return rows


def _evaluate_state(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    hits = sum(
        ((row["to"] in WORK_ORDER_TRANSITIONS.get(row["from"], set())) == row["expected_allowed"]) for row in rows
    )
    return {"total": len(rows), "transition_accuracy": round(hits / len(rows), 4)}


def _evaluate_facility(rows: list[dict[str, Any]]) -> dict[str, float | int | None]:
    category_hits = 0
    confirmation_hits = 0
    for row in rows:
        category, _, _ = classify_issue(
            TriageRequest(description=row["description"], region=row["region"], address=row.get("address"))
        )
        category_hits += category == row["expected_category"]
        confirmation_hits += (row.get("address") is None) == row["expected_requires_confirmation"]
    return {
        "total": len(rows),
        "category_accuracy": round(category_hits / len(rows), 4),
        "confirmation_accuracy": round(confirmation_hits / len(rows), 4),
        "facility_id_accuracy": None,
        "facility_id_note": "需要加载固定设施台账 fixture 后执行，Step30/31 接入数据库评测。",
    }


def _evaluate_rag_dataset(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    valid = sum(bool(row.get("relevant_terms")) and row["top_k"] > 0 for row in rows)
    return {"total": len(rows), "fixture_ready_rate": round(valid / len(rows), 4)}


def _evaluate_high_risk(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    risk_hits = 0
    confirmation_hits = 0
    for row in rows:
        result = SafetyAgent().assess(
            SafetyAssessmentRequest(
                facility_type=row["facility_type"],
                issue_type=row["issue_type"],
                work_description=row["work_description"],
                region="中心区",
                live_power=row.get("live_power", False),
                road_closure=row.get("road_closure", False),
                high_work=row.get("high_work", False),
            )
        )
        risk_hits += result.risk_level == row["expected_risk"]
        confirmation_hits += result.requires_confirmation == row["expected_confirmation"]
    return {
        "total": len(rows),
        "risk_accuracy": round(risk_hits / len(rows), 4),
        "confirmation_accuracy": round(confirmation_hits / len(rows), 4),
    }


def evaluate(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    datasets: dict[str, Any] = {}
    for definition in config["datasets"]:
        path = config_path.parent / definition["path"]
        rows = _rows(path)
        if len(rows) < definition["minimum_count"]:
            raise ValueError(f"dataset is below minimum_count: {definition['name']}")
        task = definition["task"]
        if task == "state_transition":
            metrics = _evaluate_state(rows)
        elif task == "facility_matching":
            metrics = _evaluate_facility(rows)
        elif task == "rag_retrieval":
            metrics = _evaluate_rag_dataset(rows)
        elif task == "high_risk":
            metrics = _evaluate_high_risk(rows)
        elif task == "triage":
            metrics = evaluate_triage(path)
        elif task == "sla_scheduling":
            metrics = evaluate_scheduling(path)
        elif task == "safety_acceptance":
            metrics = evaluate_safety(path)
        else:
            metrics = {"total": len(rows), "validated": True}
        datasets[definition["name"]] = {"path": str(path.relative_to(ROOT)), "task": task, "metrics": metrics}
    return {
        "benchmark_version": config["benchmark_version"],
        "dataset_version": config["dataset_version"],
        "model": config["model"],
        "parameters": config["parameters"],
        "thresholds": config["thresholds"],
        "generated_at": datetime.now(UTC).isoformat(),
        "datasets": datasets,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="evaluation/benchmark_config.json")
    parser.add_argument("--output", default="evaluation/reports/step29-baseline.json")
    args = parser.parse_args()
    result = evaluate(ROOT / args.config)
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
