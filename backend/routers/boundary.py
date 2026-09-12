from fastapi import APIRouter, HTTPException

from services.location_service import get_location
from services.weather_service import get_current_weather
from services.boundary_service import get_boundary, get_weather_color


router = APIRouter()


@router.get("/boundary")
def boundary(city: str):
    """
    Return the administrative boundary polygon for a city,
    along with current weather and a fill color based on weather condition.
    If no boundary polygon is found, still returns weather + location.
    """
    location = get_location(city)
    if not location:
        raise HTTPException(status_code=404, detail="City not found")

    try:
        weather = get_current_weather(location["latitude"], location["longitude"])
    except Exception:
        weather = {}

    condition = weather.get("condition", "")
    fill_color = get_weather_color(condition)

    response = {
        "city": location["city"],
        "country": location.get("country", ""),
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "weather": weather,
        "fill_color": fill_color,
    }

    boundary_info = get_boundary(city)
    if boundary_info:
        response["geojson"] = boundary_info["geojson"]
        response["boundary_type"] = boundary_info["boundary_type"]
        response["display_name"] = boundary_info["display_name"]

    return response
