import math
import requests
import time


def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance in km between two points
    on the earth (specified in decimal degrees).
    """
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return 6371 * c


def get_route(origin_lat, origin_lon, dest_lat, dest_lon):
    """
    Fetch the driving route from OSRM (free, no API key needed).
    Returns route geometry, total distance (km), and total duration (seconds).
    """
    url = (
        f"https://router.project-osrm.org/route/v1/driving/"
        f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
        f"?overview=full&geometries=geojson&steps=true"
    )
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            return None

        route = data["routes"][0]
        return {
            "route_geometry": route["geometry"]["coordinates"],
            "total_distance_km": route["distance"] / 1000.0,
            "total_duration_seconds": route["duration"],
        }
    except Exception as e:
        print(f"OSRM route error: {e}")
        return None


def sample_route_points(route_geometry, total_distance_km):
    """
    Sample waypoints along the route polyline.
    Interval depends on total distance:
      - Short  (< 100 km):  every ~25 km
      - Medium (100–500 km): every ~60 km
      - Long   (> 500 km):  every ~120 km
    Always includes first and last point.
    """
    if not route_geometry:
        return []

    if total_distance_km < 100:
        interval_km = 25
    elif total_distance_km <= 500:
        interval_km = 60
    else:
        interval_km = 120

    sampled = []

    # First point
    first_lon, first_lat = route_geometry[0]
    sampled.append({
        "lat": first_lat,
        "lon": first_lon,
        "cumulative_distance_km": 0.0,
    })

    cumulative = 0.0
    next_target = interval_km

    for i in range(1, len(route_geometry)):
        prev_lon, prev_lat = route_geometry[i - 1]
        curr_lon, curr_lat = route_geometry[i]
        segment = haversine(prev_lat, prev_lon, curr_lat, curr_lon)

        if cumulative + segment >= next_target:
            sampled.append({
                "lat": curr_lat,
                "lon": curr_lon,
                "cumulative_distance_km": cumulative + segment,
            })
            next_target += interval_km

        cumulative += segment

    # Last point (if not already added)
    last_lon, last_lat = route_geometry[-1]
    if sampled[-1]["lat"] != last_lat or sampled[-1]["lon"] != last_lon:
        sampled.append({
            "lat": last_lat,
            "lon": last_lon,
            "cumulative_distance_km": cumulative,
        })

    return sampled


def get_nearest_city(lat, lon):
    """
    Reverse-geocode coordinates to the nearest city name using Nominatim.
    Respects Nominatim 1 req/sec rate limit.
    """
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"lat": lat, "lon": lon, "format": "json", "zoom": 10}
    headers = {"User-Agent": "WeatherGPT/1.0"}

    try:
        time.sleep(1)  # respect Nominatim rate limit
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        address = data.get("address", {})
        return (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("county")
            or "Unknown"
        )
    except Exception as e:
        print(f"Reverse geocoding error: {e}")
        return "Unknown"
