import requests
import time
import math
import statistics
from datetime import datetime, timedelta


# =============================================
# POLYGON GEOMETRY UTILITIES
# =============================================

def is_point_in_polygon(x, y, polygon):
    """
    Ray-casting point-in-polygon test.
    x = latitude, y = longitude.
    polygon = list of [lat, lon] pairs.
    Works correctly for arbitrary convex and concave polygons.
    """
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
    Generate a regular grid of points INSIDE the polygon.
    resolution ~0.005° ≈ 500m spacing.
    Returns list of {"lat": float, "lon": float}.
    """
    if not polygon_coords or len(polygon_coords) < 3:
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


def calculate_polygon_area(polygon_coords):
    """
    Calculate polygon area using the Shoelace formula
    with degree-to-meter conversion.
    Returns (area_hectares, area_sq_km).
    """
    if not polygon_coords or len(polygon_coords) < 3:
        return 0, 0

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
    area_hectares = area_sq_meters / 10000.0
    area_sq_km = area_sq_meters / 1000000.0
    return area_hectares, area_sq_km


# =============================================
# NDVI CLASSIFICATION
# =============================================

NDVI_THRESHOLDS = {
    "healthy":   {"min": 0.6, "max": 1.0, "color": "#22c55e", "label": "Healthy"},
    "moderate":  {"min": 0.4, "max": 0.6, "color": "#eab308", "label": "Moderate"},
    "poor":      {"min": 0.2, "max": 0.4, "color": "#f97316", "label": "Poor"},
    "very_poor": {"min": -1.0, "max": 0.2, "color": "#ef4444", "label": "Very Poor"},
}


def classify_ndvi(value):
    """
    Classify NDVI value into health category with color.
    Returns (category_key, hex_color).
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


# =============================================
# MODIS SATELLITE DATA FETCHING
# =============================================

def get_ndvi_for_point(lat, lon, date_str):
    """
    Fetch NDVI from MODIS MOD13Q1 (250m resolution) via ORNL DAAC REST API.
    NDVI values are scaled: actual NDVI = raw_value * 0.0001

    Returns dict: {"ndvi": float|None, "data_date": str|None}
    The data_date is the actual satellite observation date from the MODIS response,
    which may differ from the requested date.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        
        # MOD13Q1 is a 16-day composite. To ensure we find data even if the 
        # exact requested date isn't a composite start date, we search a 32-day window.
        start_dt = dt - timedelta(days=32)
        
        start_date = f"A{start_dt.year}{start_dt.timetuple().tm_yday:03d}"
        end_date = f"A{dt.year}{dt.timetuple().tm_yday:03d}"

        url = "https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset"
        params = {
            "latitude": lat,
            "longitude": lon,
            "band": "250m_16_days_NDVI",
            "startDate": start_date,
            "endDate": end_date,
            "kmAboveBelow": 0,
            "kmLeftRight": 0,
        }

        time.sleep(0.5)  # Rate limiting for ORNL DAAC
        response = requests.get(url, params=params, timeout=15)

        if response.status_code != 200:
            return {"ndvi": None, "data_date": None}

        data = response.json()
        subset = data.get("subset", [])
        if not subset:
            return {"ndvi": None, "data_date": None}

        # The API returns a list of composites. We take the last one (closest to requested date)
        latest_entry = subset[-1]
        ndvi_raw = latest_entry.get("data", [])
        actual_date = latest_entry.get("calendar_date", None)

        if not ndvi_raw:
            return {"ndvi": None, "data_date": actual_date}

        value = ndvi_raw[0]
        # Filter fill/invalid values (MODIS fill = -3000, valid range -2000 to 10000)
        if value < -2000 or value > 10000:
            return {"ndvi": None, "data_date": actual_date}

        return {"ndvi": value * 0.0001, "data_date": actual_date}

    except Exception as e:
        print(f"NDVI fetch error ({lat}, {lon}): {e}")
        return {"ndvi": None, "data_date": None}


# =============================================
# DIRECTIONAL ANALYSIS
# =============================================

def analyze_spatial_distribution(grid_results, polygon_coords):
    """
    Analyze where low-NDVI areas are concentrated within the polygon.
    Returns a directional description string or None if not enough data.
    """
    low_ndvi_points = [
        p for p in grid_results
        if p["ndvi"] is not None and p["category"] in ("poor", "very_poor")
    ]

    if len(low_ndvi_points) < 2:
        return None

    # Calculate polygon centroid
    lats = [p[0] for p in polygon_coords]
    lons = [p[1] for p in polygon_coords]
    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)

    # Count low-NDVI points in each quadrant relative to centroid
    north = sum(1 for p in low_ndvi_points if p["lat"] > center_lat)
    south = sum(1 for p in low_ndvi_points if p["lat"] <= center_lat)
    east = sum(1 for p in low_ndvi_points if p["lon"] > center_lon)
    west = sum(1 for p in low_ndvi_points if p["lon"] <= center_lon)

    total = len(low_ndvi_points)
    if total == 0:
        return None

    # Determine dominant direction (>60% concentration)
    directions = []
    if north / total > 0.6:
        directions.append("northern")
    elif south / total > 0.6:
        directions.append("southern")
    if east / total > 0.6:
        directions.append("eastern")
    elif west / total > 0.6:
        directions.append("western")

    if directions:
        return f"Lower vegetation-index values are concentrated in the {' '.join(directions)} portion of the selected area."

    return None


# =============================================
# MAIN ANALYSIS FUNCTION
# =============================================

def analyze_ndvi(polygon_coords, requested_date):
    """
    Full NDVI analysis for a user-drawn polygon.

    Workflow:
    1. Validate polygon and calculate area
    2. Generate grid points INSIDE the polygon
    3. Fetch real MODIS NDVI for each grid point
    4. Track actual satellite observation date
    5. Classify each point into health categories
    6. Calculate comprehensive statistics (avg, median, min, max)
    7. Calculate health distribution with percentages AND area
    8. Generate spatial analysis and human-readable explanation
    9. Return full response including data availability info

    Uses REAL satellite data from MODIS MOD13Q1 — no fake values.
    """
    # 1. Calculate polygon area
    area_hectares, area_sq_km = calculate_polygon_area(polygon_coords)

    # 2. Generate grid points inside the polygon
    grid_points = generate_grid_points(polygon_coords)

    if not grid_points:
        return {"error": "No grid points could be generated within the polygon. The polygon may be too small."}

    # Cap at 50 points to avoid MODIS API overload
    if len(grid_points) > 50:
        step = max(1, len(grid_points) // 50)
        grid_points = grid_points[::step][:50]

    # 3. Fetch NDVI for each point and track data dates
    results = []
    valid_ndvi_values = []
    observed_dates = set()
    categories = {
        "healthy": 0,
        "moderate": 0,
        "poor": 0,
        "very_poor": 0,
        "no_data": 0,
    }

    for point in grid_points:
        fetch_result = get_ndvi_for_point(point["lat"], point["lon"], requested_date)
        ndvi_val = fetch_result["ndvi"]
        data_date = fetch_result["data_date"]

        if data_date:
            observed_dates.add(data_date)

        cat, color = classify_ndvi(ndvi_val)

        if ndvi_val is not None:
            valid_ndvi_values.append(ndvi_val)

        categories[cat] += 1

        results.append({
            "lat": point["lat"],
            "lon": point["lon"],
            "ndvi": round(ndvi_val, 4) if ndvi_val is not None else None,
            "category": cat,
            "color": color,
        })

    total_points = len(grid_points)
    total_valid = len(valid_ndvi_values)

    if total_points == 0:
        return {"error": "No grid points could be generated within the polygon."}

    # 4. Determine actual data date
    # MODIS returns calendar_date for each observation
    actual_data_date = None
    if observed_dates:
        # Use the most common observation date
        actual_data_date = max(observed_dates)  # Latest available

    data_available_for_requested = False
    if actual_data_date and actual_data_date == requested_date:
        data_available_for_requested = True

    # 5. Calculate statistics (ONLY from valid observations inside polygon)
    avg_ndvi = None
    median_ndvi = None
    min_ndvi = None
    max_ndvi = None

    if valid_ndvi_values:
        avg_ndvi = sum(valid_ndvi_values) / len(valid_ndvi_values)
        median_ndvi = statistics.median(valid_ndvi_values)
        min_ndvi = min(valid_ndvi_values)
        max_ndvi = max(valid_ndvi_values)

    # 6. Calculate health distribution with percentages AND area in hectares
    # Only count points that have valid NDVI data for percentage calculation
    valid_category_total = total_valid if total_valid > 0 else 1  # avoid division by zero

    health_distribution = {}
    for cat_key in ["healthy", "moderate", "poor", "very_poor"]:
        count = categories[cat_key]
        pct = round((count / valid_category_total) * 100, 1) if total_valid > 0 else 0
        cat_area = round(area_hectares * (pct / 100), 2) if area_hectares > 0 else 0
        health_distribution[cat_key] = {
            "count": count,
            "percentage": pct,
            "area_hectares": cat_area,
        }

    # 7. Determine overall health
    if avg_ndvi is None:
        overall_health = "unknown"
    elif avg_ndvi > 0.6:
        overall_health = "healthy"
    elif avg_ndvi > 0.4:
        overall_health = "moderate"
    elif avg_ndvi > 0.2:
        overall_health = "poor"
    else:
        overall_health = "very_poor"

    # 8. Generate human-readable explanation
    if avg_ndvi is None:
        explanation = (
            "NDVI satellite data is currently unavailable for this area and date. "
            "This may be due to cloud cover, data processing lag, or the satellite's "
            "observation schedule. Try selecting a date 10–16 days in the past."
        )
    else:
        # Build explanation from actual statistics
        parts = []

        # Main assessment
        health_labels = {
            "healthy": "healthy, dense vegetation",
            "moderate": "moderate vegetation health",
            "poor": "poor vegetation cover",
            "very_poor": "very poor vegetation cover",
        }
        parts.append(
            f"Your selected area ({area_hectares:.1f} ha) shows "
            f"{health_labels.get(overall_health, 'unknown vegetation status')} "
            f"with an average NDVI of {avg_ndvi:.2f}."
        )

        # Dominant category
        healthy_pct = health_distribution["healthy"]["percentage"]
        if healthy_pct > 50:
            parts.append(
                f"About {healthy_pct:.0f}% of the area falls in the healthy "
                f"vegetation category."
            )

        # Stress warning
        poor_pct = health_distribution["poor"]["percentage"]
        very_poor_pct = health_distribution["very_poor"]["percentage"]
        stress_pct = poor_pct + very_poor_pct
        if stress_pct > 10:
            parts.append(
                f"Approximately {stress_pct:.0f}% of the area has poor or very poor "
                f"vegetation-index values and may require closer observation."
            )

        # Spatial distribution
        spatial_note = analyze_spatial_distribution(results, polygon_coords)
        if spatial_note:
            parts.append(spatial_note)

        explanation = " ".join(parts)

    # 9. Build and return the complete response
    return {
        # Area info
        "area_hectares": round(area_hectares, 2),
        "area_sq_km": round(area_sq_km, 4),

        # Date & source info
        "requested_date": requested_date,
        "data_date": actual_data_date,
        "data_available_for_requested_date": data_available_for_requested,
        "data_source": "MODIS MOD13Q1 (250m resolution)",

        # NDVI statistics (calculated ONLY from valid observations inside polygon)
        "average_ndvi": round(avg_ndvi, 4) if avg_ndvi is not None else None,
        "median_ndvi": round(median_ndvi, 4) if median_ndvi is not None else None,
        "min_ndvi": round(min_ndvi, 4) if min_ndvi is not None else None,
        "max_ndvi": round(max_ndvi, 4) if max_ndvi is not None else None,

        # Overall assessment
        "overall_health": overall_health,
        "explanation": explanation,

        # Health distribution with percentage AND area
        "health_distribution": health_distribution,

        # Data quality info
        "total_points": total_points,
        "total_valid_points": total_valid,
        "no_data_points": categories["no_data"],

        # Spatial grid for map visualization
        "grid": results,
    }


# =============================================
# MODIS DATE AVAILABILITY
# =============================================

def get_modis_available_dates(lat, lon, start_date, end_date):
    """
    Query MODIS ORNL DAAC for available MOD13Q1 composite dates.
    Uses the /dates endpoint which is fast and returns all composite dates.

    Returns list of observation dicts compatible with the availability response.
    """
    try:
        url = "https://modis.ornl.gov/rst/api/v1/MOD13Q1/dates"
        params = {"latitude": lat, "longitude": lon}

        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            return []

        data = response.json()
        dates = data.get("dates", [])

        # Filter to requested date range
        observations = []
        for entry in dates:
            cal_date = entry.get("calendar_date", "")
            modis_date = entry.get("modis_date", "")

            if not cal_date:
                continue

            # Filter by date range
            if cal_date < start_date or cal_date > end_date:
                continue

            observations.append({
                "date": cal_date,
                "source": "modis",
                "satellite": "Terra",
                "cloud_cover_pct": None,  # MODIS composites don't have per-scene cloud %
                "quality": "composite",   # 16-day composite — cloud already filtered
                "usable": True,
                "scene_id": modis_date,
                "tile": "",
                "resolution": "250m",
            })

        # Sort newest first
        observations.sort(key=lambda x: x["date"], reverse=True)
        return observations

    except Exception as e:
        print(f"MODIS dates fetch error: {e}")
        return []
