from fastapi import APIRouter, HTTPException, Query
from datetime import datetime

from services.location_service import get_location
from services.route_service import get_route, sample_route_points, get_nearest_city
from services.route_weather_service import (
    get_route_weather,
    generate_weather_zones,
    generate_route_summary,
)


router = APIRouter()


@router.get("/route/weather")
def route_weather(
    origin: str = Query(..., description="Origin city name"),
    destination: str = Query(..., description="Destination city name"),
    start_time: str = Query(None, description="ISO datetime for departure"),
):
    """
    Calculate driving route from origin to destination, then provide
    TIME-AWARE weather forecasts for each zone along the journey.
    """

    # Validate: same origin/destination
    if origin.strip().lower() == destination.strip().lower():
        raise HTTPException(
            status_code=400,
            detail="Origin and destination cannot be the same city.",
        )

    # Default start time to now
    if not start_time:
        start_time = datetime.now().isoformat()

    # Geocode origin
    origin_loc = get_location(origin)
    if not origin_loc:
        raise HTTPException(status_code=404, detail=f"City not found: {origin}")

    # Geocode destination
    dest_loc = get_location(destination)
    if not dest_loc:
        raise HTTPException(status_code=404, detail=f"City not found: {destination}")

    # Get driving route from OSRM
    route_data = get_route(
        origin_loc["latitude"], origin_loc["longitude"],
        dest_loc["latitude"], dest_loc["longitude"],
    )
    if not route_data:
        raise HTTPException(
            status_code=404,
            detail="Could not calculate a driving route between these locations.",
        )

    # Sample intelligent waypoints along the route
    waypoints = sample_route_points(
        route_data["route_geometry"],
        route_data["total_distance_km"],
    )

    # Reverse-geocode each waypoint to get city names
    for wp in waypoints:
        wp["city_name"] = get_nearest_city(wp["lat"], wp["lon"])

    # Get time-aware weather for each waypoint
    waypoints_with_weather = get_route_weather(
        waypoints, start_time, route_data["total_duration_seconds"]
    )
    if not waypoints_with_weather:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch weather data for the route.",
        )

    # Generate weather zones (grouped by weather condition changes)
    zones = generate_weather_zones(waypoints_with_weather)

    # Generate journey summary
    summary = generate_route_summary(
        zones,
        route_data["total_distance_km"],
        route_data["total_duration_seconds"],
        start_time,
    )

    return {
        "origin": origin_loc,
        "destination": dest_loc,
        "total_distance_km": route_data["total_distance_km"],
        "total_duration_hours": route_data["total_duration_seconds"] / 3600.0,
        "start_time": start_time,
        "arrival_time": summary["arrival_time"],
        "route_geometry": route_data["route_geometry"],
        "zones": zones,
        "summary": summary,
    }
