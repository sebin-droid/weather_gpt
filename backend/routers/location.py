from fastapi import APIRouter, HTTPException
from services.location_service import get_location

router = APIRouter()


@router.get("/location/search")
def location_search(q: str):
    location = get_location(q)
    if location is None:
        raise HTTPException(status_code=404, detail="Location not found")
    return location
