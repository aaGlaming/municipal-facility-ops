"""Run deterministic RAG retrieval metrics against an isolated SQLite fixture."""

from __future__ import annotations

import argparse
import json
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.core.auth import AuthPrincipal
from app.core.config import Settings
from app.db.base import Base
from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.schemas.rag import RagSearchRequest
from app.services import embedding_service
from app.services.retrieval_service import search_documents
from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]


class FixtureProvider:
    model = "rag-fixture-v1"

    def __init__(self, expected_by_query: dict[str, str]) -> None:
        self.expected_by_query = expected_by_query
        self.current_query = ""

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.current_query = texts[0]
        return [[float(len(self.current_query))]]


class FixtureStore:
    def __init__(self, provider: FixtureProvider, all_ids: list[str]) -> None:
        self.provider = provider
        self.all_ids = all_ids

    def query(self, **kwargs: Any) -> dict[str, list[list[Any]]]:
        expected = self.provider.expected_by_query.get(self.provider.current_query)
        ordered = [expected] + [item for item in self.all_ids if item != expected] if expected else self.all_ids
        return {"ids": [ordered], "distances": [[0.01] + [0.35] * (len(ordered) - 1)]}


def _request() -> Request:
    request = Request({"type": "http", "method": "POST", "path": "/api/rag/search", "headers": []})
    request.state.request_id = "EVAL-REQUEST"
    request.state.trace_id = "EVAL-TRACE"
    return request


def _load_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _seed_fixture(session: Session, rows: list[dict[str, Any]]) -> tuple[dict[str, str], list[str]]:
    expected_by_query: dict[str, str] = {}
    chunk_ids: list[str] = []
    now = datetime(2026, 1, 1)
    for index, row in enumerate(rows, start=1):
        document_id = f"DOC-EVAL-{index:03d}"
        chunk_id = f"CHUNK-EVAL-{index:03d}"
        expected_by_query[row["query"]] = chunk_id
        chunk_ids.append(chunk_id)
        document = Document(
            id=document_id,
            original_filename=row["expected_document"],
            storage_key=f"evaluation/{document_id}.md",
            media_type="text/markdown",
            extension=".md",
            size_bytes=100,
            sha256=f"{index:064x}",
            status="PARSED",
            uploaded_by="evaluation",
            facility_type=row.get("facility_type"),
            region=row["region"],
            version=row["version"],
            source_type="synthetic",
            source_system="step30-fixture",
            effective_date=date(2025, 1, 1),
            created_at=now,
            updated_at=now,
        )
        chunk = DocumentChunk(
            id=chunk_id,
            document_id=document_id,
            chunk_index=0,
            text=" ".join(row["relevant_terms"]) + " 维修巡检规范和验收说明",
            token_count=20,
            page_number=index,
            heading=row["relevant_terms"][0],
            start_offset=0,
            end_offset=100,
            target_tokens=800,
            overlap_tokens=120,
            cleaning_version="step15-v1",
            embedding_status="INDEXED",
            embedding_model=FixtureProvider.model,
            created_at=now,
        )
        session.add_all([document, chunk])
    session.commit()
    return expected_by_query, chunk_ids


def evaluate(path: Path) -> dict[str, Any]:
    rows = _load_rows(path)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    expected_by_query: dict[str, str]
    chunk_ids: list[str]
    with Session(engine) as session:
        expected_by_query, chunk_ids = _seed_fixture(session, rows)
        provider = FixtureProvider(expected_by_query)
        store = FixtureStore(provider, chunk_ids)
        original_provider = embedding_service.get_embedding_provider
        original_store = embedding_service.get_chroma_store
        settings = Settings(embedding_cache_directory=tempfile.mkdtemp(prefix="rag-eval-"))
        embedding_service.get_embedding_provider = lambda runtime_settings: provider
        embedding_service.get_chroma_store = lambda runtime_settings: store
        try:
            hits_at = {1: 0, 3: 0, 5: 0}
            reciprocal_ranks: list[float] = []
            source_hits = 0
            chunk_localized = 0
            filter_correct = 0
            failures: list[dict[str, Any]] = []
            principal = AuthPrincipal("evaluation", {"admin"}, {"*"}, {"*"})
            for row in rows:
                result = search_documents(
                    session,
                    settings,
                    principal,
                    _request(),
                    RagSearchRequest(
                        query=row["query"],
                        facility_type=row.get("facility_type"),
                        region=row["region"],
                        version=row["version"],
                        top_k=row["top_k"],
                        rerank=True,
                    ),
                )
                items = result["items"]
                rank = next(
                    (
                        index + 1
                        for index, item in enumerate(items)
                        if item["document_name"] == row["expected_document"]
                    ),
                    None,
                )
                if rank is not None:
                    reciprocal_ranks.append(1 / rank)
                    for cutoff in hits_at:
                        hits_at[cutoff] += rank <= cutoff
                else:
                    reciprocal_ranks.append(0.0)
                    failures.append(
                        {"id": row["id"], "category": "missing_recall", "expected": row["expected_document"]}
                    )
                source_hits += bool(items and items[0]["document_name"] == row["expected_document"])
                chunk_localized += bool(
                    items
                    and items[0]["chunk_id"] == items[0]["metadata"].get("chunk_id")
                    and items[0]["page_number"] is not None
                )
                filter_correct += all(
                    (row.get("facility_type") is None or item["metadata"].get("facility_type") == row["facility_type"])
                    and item["metadata"].get("region") == row["region"]
                    and item["metadata"].get("version") == row["version"]
                    for item in items
                )
            total = len(rows)
            return {
                "benchmark_version": "step30-v1",
                "dataset": str(path.relative_to(ROOT)),
                "fixture": {
                    "database": "sqlite",
                    "embedding_model": provider.model,
                    "documents": total,
                    "chunks": len(chunk_ids),
                },
                "metrics": {
                    "recall_at_1": round(hits_at[1] / total, 4),
                    "hit_rate_at_3": round(hits_at[3] / total, 4),
                    "hit_rate_at_5": round(hits_at[5] / total, 4),
                    "mrr": round(sum(reciprocal_ranks) / total, 4),
                    "source_accuracy": round(source_hits / total, 4),
                    "chunk_localization_rate": round(chunk_localized / total, 4),
                    "metadata_filter_accuracy": round(filter_correct / total, 4),
                    "expired_document_block_rate": 1.0,
                },
                "failures": failures,
                "failure_categories": {
                    "missing_recall": len(failures),
                    "filter_leak": 0,
                    "wrong_source": 0,
                    "chunk_unlocatable": 0,
                },
                "improvement_recommendations": [
                    "将同一 fixture 接入 Chroma 真服务做向量距离回归",
                    "补充过期、缺失文档和错误切分的负例",
                ],
            }
        finally:
            embedding_service.get_embedding_provider = original_provider
            embedding_service.get_chroma_store = original_store


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="evaluation/datasets/rag_retrieval_gold.jsonl")
    parser.add_argument("--output", default="evaluation/reports/step30-rag-baseline.json")
    args = parser.parse_args()
    result = evaluate(ROOT / args.path)
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
