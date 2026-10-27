from app.core.auth import issue_access_token
from app.core.config import Settings
from fastapi.testclient import TestClient


def _headers(*permissions: str) -> dict[str, str]:
    token = issue_access_token("chunk-user", ["auditor"], list(permissions), ["*"], Settings().auth_secret, 900)
    return {"Authorization": f"Bearer {token}"}


def _upload(client: TestClient) -> str:
    response = client.post(
        "/api/rag/documents",
        files={
            "file": (
                "long.md",
                (
                    b"Page header\n\n# Repair rule\n\n"
                    b"Alpha sentence with invisible\xe2\x80\x8b\xe2\x80\x8f characters.\n\n"
                    b"Page footer\n\nPage header\n\n"
                    b"Beta sentence contains enough words to force multiple chunks. "
                    b"Gamma sentence continues the same operational rule with details. "
                    b"Delta sentence closes the rule.\n\nPage footer"
                ),
                "text/markdown",
            )
        },
        headers=_headers("document:upload"),
    )
    assert response.status_code == 201
    return response.json()["item"]["id"]


def test_chunk_preview_cleans_repeated_headers_and_returns_source_metadata(client: TestClient) -> None:
    document_id = _upload(client)
    response = client.get(
        f"/api/rag/documents/{document_id}/chunks/preview?target_tokens=20&overlap_tokens=5",
        headers=_headers("document:read"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["target_tokens"] == 20
    assert body["overlap_tokens"] == 5
    assert len(body["items"]) >= 2
    assert all("Page header" not in item["text"] for item in body["items"])
    assert all("\u200f" not in item["text"] for item in body["items"])
    assert all(item["document_id"] == document_id for item in body["items"])
    assert all(item["chunk_index"] == index for index, item in enumerate(body["items"]))
    assert all(item["token_count"] <= 23 for item in body["items"])
    assert body["items"][0]["heading"] == "Repair rule"


def test_regenerate_chunks_persists_adjusted_parameters_and_is_readable(client: TestClient) -> None:
    document_id = _upload(client)
    regenerated = client.post(
        f"/api/rag/documents/{document_id}/chunks/regenerate",
        json={"target_tokens": 20, "overlap_tokens": 5},
        headers=_headers("document:chunk"),
    )
    assert regenerated.status_code == 200
    assert regenerated.json()["target_tokens"] == 20
    listed = client.get(f"/api/rag/documents/{document_id}/chunks", headers=_headers("document:read"))
    assert listed.status_code == 200
    assert listed.json()["target_tokens"] == 20
    assert listed.json()["items"]
    assert listed.json()["items"][0]["source_part_id"]


def test_chunk_parameters_are_bounded(client: TestClient) -> None:
    document_id = _upload(client)
    response = client.get(
        f"/api/rag/documents/{document_id}/chunks/preview?target_tokens=1&overlap_tokens=4",
        headers=_headers("document:read"),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
