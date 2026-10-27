from app.core.auth import issue_access_token
from app.core.config import Settings
from app.services import embedding_service
from fastapi.testclient import TestClient


def _headers(*permissions: str) -> dict[str, str]:
    token = issue_access_token("search-user", ["admin"], list(permissions), ["*"], Settings().auth_secret, 900)
    return {"Authorization": f"Bearer {token}"}


class FakeProvider:
    model = "fake-search-v1"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, float(len(text))] for text in texts]


class FakeStore:
    def __init__(self) -> None:
        self.ids: list[str] = []

    def upsert(self, **kwargs) -> None:
        self.ids = list(kwargs["ids"])

    def query(self, **kwargs) -> dict:
        return {"ids": [self.ids], "distances": [[0.1 for _ in self.ids]]}

    def delete(self, ids: list[str]) -> None:
        self.ids = [item for item in self.ids if item not in ids]


def _indexed_document(client: TestClient, monkeypatch) -> tuple[str, FakeStore]:
    provider = FakeProvider()
    store = FakeStore()
    monkeypatch.setattr(embedding_service, "get_embedding_provider", lambda settings: provider)
    monkeypatch.setattr(embedding_service, "get_chroma_store", lambda settings: store)
    upload = client.post(
        "/api/rag/documents",
        files={"file": ("search.md", b"# Street light\n\nRepair procedure for street_light assets.", "text/markdown")},
        data={"facility_type": "street_light", "region": "DISTRICT-01", "version": "v2"},
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
    indexed = client.post(f"/api/rag/documents/{document_id}/embeddings/rebuild", headers=_headers("document:embed"))
    assert indexed.status_code == 200
    return document_id, store


def test_hybrid_search_returns_source_metadata_and_debug(client: TestClient, monkeypatch) -> None:
    document_id, store = _indexed_document(client, monkeypatch)
    response = client.post(
        "/api/rag/search",
        json={"query": "street_light repair DISTRICT-01 v2", "top_k": 5, "rerank": True},
        headers=_headers("document:read"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "OK"
    assert body["filters"]["region"] == "DISTRICT-01"
    assert body["filters"]["version"] == "v2"
    assert body["items"][0]["document_id"] == document_id
    assert body["items"][0]["document_name"] == "search.md"
    assert body["items"][0]["metadata"]["facility_type"] == "street_light"
    debug = client.post(
        "/api/rag/search/debug",
        json={"query": "street_light repair", "top_k": 5},
        headers=_headers("document:read"),
    )
    assert debug.status_code == 200
    assert debug.json()["debug"]["merged_count"] >= 1
    assert store.ids


def test_search_requires_document_read_permission(client: TestClient) -> None:
    response = client.post("/api/rag/search", json={"query": "street_light"}, headers=_headers("document:upload"))
    assert response.status_code == 403
    assert response.json()["code"] == "PERMISSION_DENIED"


def test_empty_region_scope_cannot_retrieve_documents(client: TestClient, monkeypatch) -> None:
    _indexed_document(client, monkeypatch)
    token = issue_access_token("no-region", ["viewer"], ["document:read"], [], Settings().auth_secret, 900)
    response = client.post(
        "/api/rag/search",
        json={"query": "street_light repair"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "NO_RECALL"
    assert response.json()["items"] == []
