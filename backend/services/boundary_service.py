import requests
import time


def get_boundary(place_name):
    """
    Fetch administrative boundary GeoJSON polygon from OpenStreetMap via Nominatim.
    Handles ambiguity between city/taluk/district/state boundaries —
    prefers administrative boundaries with usable polygons.
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": place_name,
        "format": "json",
        "polygon_geojson": 1,
        "limit": 5,
        "countrycodes": "in",
    }
    headers = {"User-Agent": "WeatherGPT/1.0"}

    time.sleep(1)  # Respect Nominatim 1 req/sec rate limit

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        results = response.json()

        if not results:
            return None

        best_match = None

        # First pass: look for administrative boundary with usable polygon
        for res in results:
            if res.get("class") == "boundary" and res.get("type") == "administrative":
                geojson = res.get("geojson")
                if geojson and geojson.get("type") in ("Polygon", "MultiPolygon"):
                    best_match = res
                    break

        # Second pass: any result with a usable polygon
        if not best_match:
            for res in results:
                geojson = res.get("geojson")
                if geojson and geojson.get("type") in ("Polygon", "MultiPolygon"):
                    best_match = res
                    break

        if not best_match:
            return None

        return {
            "place_name": place_name,
            "display_name": best_match.get("display_name"),
            "boundary_type": best_match.get("addresstype", "unknown"),
            "geojson": best_match.get("geojson"),
            "bbox": best_match.get("boundingbox"),
        }

    except Exception as e:
        print(f"Boundary fetch error: {e}")
        return None


def get_weather_color(condition):
    """
    Map weather condition string to a hex color for polygon styling.
    """
    c = condition.lower() if condition else ""

    if any(x in c for x in ["heavy rain", "violent rain"]):
        return "#1e40af"
    elif any(x in c for x in ["moderate rain", "rain shower"]):
        return "#3b82f6"
    elif any(x in c for x in ["slight rain", "light drizzle", "drizzle"]):
        return "#60a5fa"
    elif "thunderstorm" in c:
        return "#7c3aed"
    elif "snow" in c:
        return "#bfdbfe"
    elif any(x in c for x in ["overcast", "fog"]):
        return "#9ca3af"
    elif "partly cloudy" in c:
        return "#fbbf24"
    elif "mainly clear" in c:
        return "#f59e0b"
    elif "clear sky" in c:
        return "#f97316"

    return "#6b7280"
