from app.core.auth import issue_access_token
from app.core.config import Settings
from app.services import embedding_service
from fastapi.testclient import TestClient


def _headers(*permissions: str) -> dict[str, str]:
    token = issue_access_token("embedding-user", ["admin"], list(permissions), ["*"], Settings().auth_secret, 900)
    return {"Authorization": f"Bearer {token}"}


def _document_with_chunks(client: TestClient) -> str:
    upload = client.post(
        "/api/rag/documents",
        files={"file": ("embedding.md", b"# Rule\n\nEmbedding this operational text.", "text/markdown")},
        headers=_headers("document:upload"),
    )
    assert upload.status_code == 201
    document_id = upload.json()["item"]["id"]
    chunks = client.post(
        f"/api/rag/documents/{document_id}/chunks/regenerate",
        json={"target_tokens": 20, "overlap_tokens": 2},
        headers=_headers("document:chunk"),
    )
    assert chunks.status_code == 200
    return document_id


class FakeProvider:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.model = "fake-embedding-v1-failing" if should_fail else "fake-embedding-v1"
        self.calls = 0

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        if self.should_fail:
            raise embedding_service.EmbeddingProviderError("provider unavailable", retryable=True)
        return [[float(len(text)), float(index)] for index, text in enumerate(texts)]


class FakeStore:
    def __init__(self) -> None:
        self.upserts: list[dict] = []
        self.deleted: list[str] = []

    def upsert(self, **kwargs) -> None:
        self.upserts.append(kwargs)

    def delete(self, ids: list[str]) -> None:
        self.deleted.extend(ids)


def test_embedding_rebuild_batches_chunks_writes_metadata_and_uses_cache(client: TestClient, monkeypatch) -> None:
    provider = FakeProvider()
    store = FakeStore()
    monkeypatch.setattr(embedding_service, "get_embedding_provider", lambda settings: provider)
    monkeypatch.setattr(embedding_service, "get_chroma_store", lambda settings: store)
    document_id = _document_with_chunks(client)
    first = client.post(f"/api/rag/documents/{document_id}/embeddings/rebuild", headers=_headers("document:embed"))
    assert first.status_code == 200
    assert first.json()["status"] == "INDEXED"
    assert first.json()["embedded_count"] >= 1
    assert store.upserts[0]["metadatas"][0]["document_id"] == document_id
    calls_after_first = provider.calls
    second = client.post(f"/api/rag/documents/{document_id}/embeddings/rebuild", headers=_headers("document:embed"))
    assert second.status_code == 200
    assert provider.calls == calls_after_first


def test_embedding_failure_keeps_batch_retryable_and_does_not_write_partial_vectors(
    client: TestClient, monkeypatch
) -> None:
    provider = FakeProvider(should_fail=True)
    store = FakeStore()
    monkeypatch.setattr(embedding_service, "get_embedding_provider", lambda settings: provider)
    monkeypatch.setattr(embedding_service, "get_chroma_store", lambda settings: store)
    document_id = _document_with_chunks(client)
    response = client.post(f"/api/rag/documents/{document_id}/embeddings/rebuild", headers=_headers("document:embed"))
    assert response.status_code == 503
    assert response.json()["code"] == "EMBEDDING_FAILED"
    assert response.json()["retryable"] is True
    assert not store.upserts


def test_embedding_delete_removes_document_vectors(client: TestClient, monkeypatch) -> None:
    provider = FakeProvider()
    store = FakeStore()
    monkeypatch.setattr(embedding_service, "get_embedding_provider", lambda settings: provider)
    monkeypatch.setattr(embedding_service, "get_chroma_store", lambda settings: store)
    document_id = _document_with_chunks(client)
    indexed = client.post(f"/api/rag/documents/{document_id}/embeddings/rebuild", headers=_headers("document:embed"))
    assert indexed.status_code == 200
    deleted = client.delete(f"/api/rag/documents/{document_id}/embeddings", headers=_headers("document:embed"))
    assert deleted.status_code == 200
    assert deleted.json()["deleted_count"] >= 1
    assert store.deleted
