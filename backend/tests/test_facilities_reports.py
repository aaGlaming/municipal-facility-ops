from app.core.auth import issue_access_token
from app.core.config import Settings
from fastapi.testclient import TestClient


def _headers(*permissions: str, regions: tuple[str, ...] = ("*",)) -> dict[str, str]:
    token = issue_access_token(
        "user-test", ["dispatcher"], list(permissions), list(regions), Settings().auth_secret, 900
    )
    return {"Authorization": f"Bearer {token}"}


def test_facility_list_filters_paginates_and_enforces_region_scope(client: TestClient) -> None:
    response = client.get(
        "/api/facilities?page=1&page_size=1&type=street_light",
        headers=_headers("facility:read", regions=("DISTRICT-01",)),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == "FAC-1"
    denied = client.get(
        "/api/facilities?region=DISTRICT-02", headers=_headers("facility:read", regions=("DISTRICT-01",))
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "REGION_SCOPE_DENIED"


def test_facility_detail_and_history_are_database_backed(client: TestClient) -> None:
    created = client.post(
        "/api/reports",
        json={"description": "Light is out", "category": "lighting", "facility_id": "FAC-1"},
        headers=_headers("report:create", "facility:read"),
    )
    assert created.status_code == 201
    detail = client.get("/api/facilities/FAC-1", headers=_headers("facility:read"))
    assert detail.status_code == 200
    assert detail.json()["item"]["location"]["address"] == "10 Main Street"
    history = client.get("/api/facilities/FAC-1/events", headers=_headers("facility:read"))
    assert history.status_code == 200
    assert history.json()["total"] == 1
    assert history.json()["items"][0]["description"] == "Light is out"


def test_nearby_facilities_uses_distance_radius_and_filters(client: TestClient) -> None:
    response = client.get(
        "/api/facilities/nearby?latitude=40.7001&longitude=-74.0001&radius_meters=100",
        headers=_headers("facility:read", regions=("DISTRICT-01",)),
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == ["FAC-1"]


def test_report_creation_preserves_original_and_structured_fields_and_deduplicates(client: TestClient) -> None:
    payload = {
        "description": "  Water is leaking near the curb. ",
        "category": "water",
        "subcategory": "leak",
        "facility_id": "FAC-1",
        "source": "mobile",
        "external_id": "EXT-100",
        "idempotency_key": "idem-100",
    }
    created = client.post("/api/reports", json=payload, headers=_headers("report:create"))
    assert created.status_code == 201
    item = created.json()["item"]
    assert item["description"] == payload["description"]
    assert item["category"] == "water"
    assert item["source_type"] == "internal"
    assert item["source_system"] == "municipal-facility-ops"
    repeated = client.post("/api/reports", json=payload, headers=_headers("report:create"))
    assert repeated.status_code == 200
    assert repeated.json()["item"]["id"] == item["id"]
    duplicate_external = client.post(
        "/api/reports",
        json={**payload, "idempotency_key": "idem-101"},
        headers=_headers("report:create"),
    )
    assert duplicate_external.status_code == 409
    assert duplicate_external.json()["code"] == "DUPLICATE_EXTERNAL_ID"


def test_report_duplicate_candidate_and_status_transition(client: TestClient) -> None:
    headers = _headers("report:create", "report:read", "report:update")
    first = client.post(
        "/api/reports",
        json={"description": "Broken streetlight", "category": "lighting", "facility_id": "FAC-1"},
        headers=headers,
    )
    second = client.post(
        "/api/reports",
        json={"description": "Broken streetlight", "category": "lighting", "facility_id": "FAC-1"},
        headers=headers,
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["duplicate_of"] == first.json()["item"]["id"]
    report_id = first.json()["item"]["id"]
    updated = client.patch(f"/api/reports/{report_id}/status", json={"status": "TRIAGED"}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["item"]["status"] == "TRIAGED"
    invalid = client.patch(f"/api/reports/{report_id}/status", json={"status": "NEW"}, headers=headers)
    assert invalid.status_code == 409


def test_public_import_is_deduplicated_by_source_and_keeps_source_type(client: TestClient) -> None:
    headers = _headers("report:import", "report:read")
    payload = {
        "rows": [
            {
                "description": "Public pothole event",
                "category": "road_surface",
                "source": "nyc_311",
                "external_id": "NYC-1",
                "region": "DISTRICT-01",
                "latitude": 40.7001,
                "longitude": -74.0001,
            }
        ]
    }
    imported = client.post("/api/reports/import/public", json=payload, headers=headers)
    assert imported.status_code == 200
    assert imported.json()["created"] == 1
    listed = client.get("/api/reports?source_type=public", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["items"][0]["source_type"] == "public"
    repeated = client.post("/api/reports/import/public", json=payload, headers=headers)
    assert repeated.status_code == 200
    assert repeated.json()["created"] == 0
    other_source = client.post(
        "/api/reports/import/public",
        json={"rows": [{**payload["rows"][0], "source": "other_open_data"}]},
        headers=headers,
    )
    assert other_source.status_code == 200
    assert other_source.json()["created"] == 1
