from fastapi import APIRouter, Depends, Query, Request

from app.core.auth import AuthPrincipal, ensure_region_access, require_permission

router = APIRouter(prefix="/api/facilities", tags=["facilities"])

FACILITIES = [
    {
        "id": "FAC-00001",
        "type": "street_light",
        "name": "Central Avenue Light 01",
        "source_type": "synthetic",
        "region": "DISTRICT-01",
    },
    {
        "id": "FAC-00002",
        "type": "traffic_signal",
        "name": "Central Avenue Signal 01",
        "source_type": "synthetic",
        "region": "DISTRICT-01",
    },
    {
        "id": "PUBLIC-311-00001",
        "type": "road_surface",
        "name": "Public historical event",
        "source_type": "public",
        "region": "PUBLIC",
    },
]


@router.get("")
def list_facilities(
    request: Request,
    source_type: str | None = Query(default=None),
    region: str | None = Query(default=None),
    principal: AuthPrincipal = Depends(require_permission("facility:read")),
) -> dict:
    ensure_region_access(principal, region, request)
    items = [
        item
        for item in FACILITIES
        if (source_type is None or item["source_type"] == source_type)
        and (region is None or item["region"] == region)
        and principal.can_access_region(item["region"])
    ]
    if (
        not items
        and region is None
        and principal.regions
        and "*" not in principal.regions
        and "admin" not in principal.roles
    ):
        ensure_region_access(principal, "__no_matching_region__", request)
    return {"items": items, "total": len(items), "trace_id": request.state.trace_id}
