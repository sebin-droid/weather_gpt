from fastapi import APIRouter, HTTPException
from services.location_service import get_location

router = APIRouter()


@router.get("/location/search")
def location_search(q: str):
    """
    Search for a city by name and return its coordinates.

    Usage: GET /location/search?q=kochi
    Returns: { city, country, latitude, longitude }
    Raises: 404 if city not found
    """
    location = get_location(q)

    if location is None:
        raise HTTPException(status_code=404, detail="Location not found")

    return location
