import requests
import time
import math
from datetime import datetime


def is_point_in_polygon(x, y, polygon):
    """Ray-casting point-in-polygon test."""
    inside = False
    n = len(polygon)
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def generate_grid_points(polygon_coords, resolution=0.005):
    """
    Generate a grid of points INSIDE the polygon.
    resolution ~0.005° ≈ 500 m spacing.
    """
    if not polygon_coords:
        return []

    lats = [p[0] for p in polygon_coords]
    lons = [p[1] for p in polygon_coords]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    grid = []
    lat = min_lat
    while lat <= max_lat:
        lon = min_lon
        while lon <= max_lon:
            if is_point_in_polygon(lat, lon, polygon_coords):
                grid.append({"lat": round(lat, 6), "lon": round(lon, 6)})
            lon += resolution
        lat += resolution

    return grid


def get_ndvi_for_point(lat, lon, date_str):
    """
    Fetch NDVI from MODIS/VIIRS (MOD13Q1, 250m resolution) via ORNL DAAC.
    NDVI values are scaled: actual NDVI = value * 0.0001
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        doy = dt.timetuple().tm_yday
        modis_date = f"A{dt.year}{doy:03d}"

        url = "https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset"
        params = {
            "latitude": lat,
            "longitude": lon,
            "band": "250m_16_days_NDVI",
            "startDate": modis_date,
            "endDate": modis_date,
            "kmAboveBelow": 0,
            "kmLeftRight": 0,
        }

        time.sleep(0.5)  # Rate limiting
        response = requests.get(url, params=params, timeout=15)

        if response.status_code != 200:
            return None

        data = response.json()
        subset = data.get("subset", [])
        if not subset:
            return None

        ndvi_data = subset[0].get("data", [])
        if not ndvi_data:
            return None

        value = ndvi_data[0]
        # Filter fill/invalid values
        if value < -2000 or value > 10000:
            return None

        return value * 0.0001

    except Exception as e:
        print(f"NDVI fetch error ({lat}, {lon}): {e}")
        return None


def classify_ndvi(value):
    """
    Classify NDVI value into health category with color.
    Returns (category, hex_color).
    """
    if value is None:
        return "no_data", "#d1d5db"
    if value > 0.6:
        return "healthy", "#22c55e"
    elif value > 0.4:
        return "moderate", "#eab308"
    elif value > 0.2:
        return "poor", "#f97316"
    else:
        return "very_poor", "#ef4444"


def calculate_polygon_area(polygon_coords):
    """
    Calculate polygon area in hectares using the Shoelace formula
    with degree-to-meter conversion.
    """
    if not polygon_coords or len(polygon_coords) < 3:
        return 0

    R = 6378137  # Earth radius in meters

    area = 0
    n = len(polygon_coords)
    for i in range(n):
        lat1, lon1 = polygon_coords[i]
        lat2, lon2 = polygon_coords[(i + 1) % n]

        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        x1 = R * lon1_rad * math.cos(lat1_rad)
        y1 = R * lat1_rad
        x2 = R * lon2_rad * math.cos(lat2_rad)
        y2 = R * lat2_rad

        area += x1 * y2 - x2 * y1

    area_sq_meters = abs(area) / 2.0
    return area_sq_meters / 10000.0  # Convert to hectares


def analyze_ndvi(polygon_coords, date_str):
    """
    Full NDVI analysis for a user-drawn polygon.
    Generates grid → fetches NDVI per point → classifies → summarizes.
    Uses REAL satellite data from MODIS — no fake values.
    """
    area_hectares = calculate_polygon_area(polygon_coords)

    grid_points = generate_grid_points(polygon_coords)

    if not grid_points:
        return {"error": "No grid points could be generated within the polygon."}

    # Cap at 50 points to avoid API overload
    if len(grid_points) > 50:
        step = max(1, len(grid_points) // 50)
        grid_points = grid_points[::step][:50]

    results = []
    valid_ndvi_values = []
    categories = {
        "healthy": 0,
        "moderate": 0,
        "poor": 0,
        "very_poor": 0,
        "no_data": 0,
    }

    for point in grid_points:
        ndvi = get_ndvi_for_point(point["lat"], point["lon"], date_str)
        cat, color = classify_ndvi(ndvi)

        if ndvi is not None:
            valid_ndvi_values.append(ndvi)

        categories[cat] += 1

        results.append({
            "lat": point["lat"],
            "lon": point["lon"],
            "ndvi": round(ndvi, 4) if ndvi is not None else None,
            "category": cat,
            "color": color,
        })

    total_points = len(grid_points)
    if total_points == 0:
        return {"error": "No grid points could be generated within the polygon."}

    # Calculate percentages (exclude no_data from breakdown display)
    breakdown = {}
    for k, v in categories.items():
        if k != "no_data":
            breakdown[k] = round((v / total_points) * 100, 1)

    avg_ndvi = sum(valid_ndvi_values) / len(valid_ndvi_values) if valid_ndvi_values else None

    # Generate human-readable explanation
    if avg_ndvi is None:
        health = "unknown"
        explanation = (
            "No satellite data is currently available for this area and date. "
            "This may be due to cloud cover or data processing lag. "
            "Try selecting a date 10-16 days in the past."
        )
    elif avg_ndvi > 0.6:
        health = "healthy"
        explanation = (
            "Most of the selected area shows healthy, dense vegetation. "
            "Crop or plant growth appears strong and well-established."
        )
    elif avg_ndvi > 0.4:
        health = "moderate"
        explanation = (
            "The selected area shows moderate vegetation health. "
            "Some parts may be experiencing mild stress from weather or soil conditions."
        )
    elif avg_ndvi > 0.2:
        health = "poor"
        explanation = (
            "The selected area has poor vegetation cover. "
            "Plants may be under significant stress, or the area may have sparse vegetation."
        )
    else:
        health = "very_poor"
        explanation = (
            "The selected area has very poor vegetation cover, "
            "suggesting mostly bare soil, fallow land, or severely stressed vegetation."
        )

    return {
        "area_hectares": round(area_hectares, 2),
        "average_ndvi": round(avg_ndvi, 4) if avg_ndvi is not None else None,
        "health": health,
        "breakdown": breakdown,
        "grid": results,
        "explanation": explanation,
    }
