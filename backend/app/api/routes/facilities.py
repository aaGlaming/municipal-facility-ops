from fastapi import APIRouter, Query, Request


router = APIRouter(prefix="/api/facilities", tags=["facilities"])

FACILITIES = [
    {"id": "FAC-00001", "type": "street_light", "name": "Central Avenue Light 01", "source_type": "synthetic"},
    {"id": "FAC-00002", "type": "traffic_signal", "name": "Central Avenue Signal 01", "source_type": "synthetic"},
    {"id": "PUBLIC-311-00001", "type": "road_surface", "name": "Public historical event", "source_type": "public"},
]


@router.get("")
def list_facilities(request: Request, source_type: str | None = Query(default=None)) -> dict:
    items = [item for item in FACILITIES if source_type is None or item["source_type"] == source_type]
    return {"items": items, "total": len(items), "trace_id": request.state.trace_id}
