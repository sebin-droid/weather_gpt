"""
NDVI Router — Vegetation health analysis endpoints.

POST /ndvi/availability — Get available satellite observation dates for a polygon
POST /ndvi/analyze     — Run NDVI analysis for a polygon on a specific date
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta

from services.ndvi_service import (
    analyze_ndvi,
    calculate_polygon_area,
    get_modis_available_dates,
)
from services.sentinel_service import search_sentinel2_scenes


router = APIRouter()


# =============================================
# REQUEST MODELS
# =============================================

class AvailabilityRequest(BaseModel):
    polygon: List[List[float]]        # [[lat, lon], ...]
    start_date: Optional[str] = None  # YYYY-MM-DD, default: 60 days ago
    end_date: Optional[str] = None    # YYYY-MM-DD, default: today


class NDVIRequest(BaseModel):
    polygon: List[List[float]]        # [[lat, lon], ...]
    date: Optional[str] = None        # YYYY-MM-DD
    source: Optional[str] = "auto"    # "sentinel", "modis", "auto"
    scene_id: Optional[str] = None    # From availability (for Phase 2 Sentinel)


# =============================================
# POLYGON VALIDATION (shared)
# =============================================

def validate_polygon(polygon):
    """Validate polygon coordinates. Returns area_ha. Raises HTTPException on error."""
    if not polygon or len(polygon) < 3:
        raise HTTPException(
            status_code=400,
            detail="Polygon must have at least 3 coordinate pairs [lat, lon].",
        )

    for point in polygon:
        if len(point) != 2:
            raise HTTPException(
                status_code=400,
                detail="Each polygon point must be [latitude, longitude].",
            )
        lat, lon = point
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid coordinates: [{lat}, {lon}]. Latitude must be -90 to 90, longitude -180 to 180.",
            )

    area_ha, _ = calculate_polygon_area(polygon)
    if area_ha > 10000:
        raise HTTPException(
            status_code=400,
            detail=f"Polygon too large ({area_ha:.0f} ha). Maximum is 10,000 hectares.",
        )
    if area_ha < 0.01:
        raise HTTPException(
            status_code=400,
            detail="Polygon too small. Please draw a larger area.",
        )

    return area_ha


# =============================================
# AVAILABILITY ENDPOINT
# =============================================

@router.post("/ndvi/availability")
def ndvi_availability(request: AvailabilityRequest):
    """
    Get available satellite observation dates for a user-drawn polygon.

    Searches:
    1. Sentinel-2 L2A scenes via Copernicus STAC (FREE, no auth)
    2. MODIS MOD13Q1 composite dates via ORNL DAAC (FREE, no auth)

    Returns observations sorted newest-first with cloud quality indicators.
    """
    area_ha = validate_polygon(request.polygon)

    # Default date range: last 90 days (MODIS can lag 6-8 weeks behind current date)
    end_date = request.end_date
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    start_date = request.start_date
    if not start_date:
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

    # Validate date formats
    for label, date_str in [("start_date", start_date), ("end_date", end_date)]:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid {label} format '{date_str}'. Use YYYY-MM-DD.",
            )

    # 1. Search Sentinel-2 scenes (free STAC search)
    sentinel_obs = search_sentinel2_scenes(request.polygon, start_date, end_date)

    # 2. Get MODIS available dates using polygon centroid
    lats = [p[0] for p in request.polygon]
    lons = [p[1] for p in request.polygon]
    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)
    modis_obs = get_modis_available_dates(center_lat, center_lon, start_date, end_date)

    # Merge all observations, sorted newest first
    all_observations = sentinel_obs + modis_obs
    all_observations.sort(key=lambda x: x["date"], reverse=True)

    return {
        "observations": all_observations,
        "polygon_area_hectares": round(area_ha, 2),
        "date_range": {"start": start_date, "end": end_date},
        "sources_checked": ["sentinel-2", "modis"],
        "sentinel_count": len(sentinel_obs),
        "modis_count": len(modis_obs),
    }


# =============================================
# ANALYZE ENDPOINT
# =============================================

@router.post("/ndvi/analyze")
def ndvi_analyze(request: NDVIRequest):
    """
    Analyze vegetation health (NDVI) for a user-drawn polygon.

    Phase 1: Uses MODIS MOD13Q1 data (no auth needed).
    Phase 2: Will add Sentinel-2 B4/B8 analysis (requires Copernicus auth).

    IMPORTANT: The user may select a Sentinel-2 date from the availability
    calendar. Since we're using MODIS in Phase 1, we look up the nearest
    actual MODIS composite date automatically and report both dates clearly.
    Never silently substitutes dates.
    """
    area_ha = validate_polygon(request.polygon)

    # Requested date from user selection
    requested_date = request.date
    if not requested_date:
        requested_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

    try:
        datetime.strptime(requested_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD.",
        )

    source = request.source or "auto"

    try:
        # -------------------------------------------------------
        # Phase 2: Sentinel-2 Analysis
        # -------------------------------------------------------
        if source and "sentinel" in source.lower() or (source == "auto" and "sentinel" in str(request.scene_id).lower() if request.scene_id else False):
            from services.sentinel_service import analyze_sentinel_ndvi
            result = analyze_sentinel_ndvi(request.polygon, requested_date)
            
            if result.get("error"):
                raise HTTPException(status_code=400, detail=result["error"])
                
            # Add enriched metadata for Sentinel response
            result["requested_date"] = requested_date
            result["data_available_for_requested_date"] = True
            result["resolution"] = "10m"
            result["satellite"] = "Sentinel-2 L2A"
            result["source_used"] = "sentinel"
            result["source_note"] = "Using Sentinel-2 10m high-resolution real-time processing via Copernicus Data Space."
            result["data_source"] = "Sentinel-2 L2A (10m resolution)"
            return result

        # Polygon centroid for MODIS date lookup
        lats = [p[0] for p in request.polygon]
        lons = [p[1] for p in request.polygon]
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)

        # Find available MODIS dates in a 90-day window ending on requested_date.
        # MODIS MOD13Q1 processing can lag 6-8 weeks behind the current date,
        # so we need a wide window to find the latest processed composite.
        req_dt = datetime.strptime(requested_date, "%Y-%m-%d")
        modis_search_start = (req_dt - timedelta(days=90)).strftime("%Y-%m-%d")
        modis_dates = get_modis_available_dates(
            center_lat, center_lon, modis_search_start, requested_date
        )

        # The nearest MODIS composite on or before the requested date
        actual_modis_date = modis_dates[0]["date"] if modis_dates else None

        if not actual_modis_date:
            # No MODIS data found at all — return explicit no-data response
            return {
                "area_hectares": round(area_ha, 2),
                "area_sq_km": round(area_ha / 100, 4),
                "requested_date": requested_date,
                "data_date": None,
                "data_available_for_requested_date": False,
                "data_source": "MODIS MOD13Q1 (250m resolution)",
                "resolution": "250m",
                "satellite": "Terra (MODIS)",
                "average_ndvi": None,
                "median_ndvi": None,
                "min_ndvi": None,
                "max_ndvi": None,
                "overall_health": "unknown",
                "explanation": (
                    "No MODIS MOD13Q1 composites were found for this area in the last 60 days. "
                    "MODIS data may not yet be processed for recent dates. "
                    "Try selecting an older date from the availability calendar."
                ),
                "health_distribution": {},
                "total_points": 0,
                "total_valid_points": 0,
                "no_data_points": 0,
                "grid": [],
                "source_used": "modis",
                "source_note": (
                    "Using MODIS MOD13Q1 (250m resolution). "
                    "Sentinel-2 (10m) will be available after Copernicus credentials are configured."
                ),
            }

        # Run MODIS analysis using the actual composite date
        result = analyze_ndvi(request.polygon, actual_modis_date)

        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])

        # Override the dates to be transparent with the user
        result["requested_date"] = requested_date
        # data_date is set by analyze_ndvi from the MODIS API response
        result["data_available_for_requested_date"] = (
            result.get("data_date") == requested_date
        )

        # Add enriched metadata
        result["resolution"] = "250m"
        result["satellite"] = "Terra (MODIS)"
        result["source_used"] = "modis"
        result["source_note"] = (
            "Using MODIS MOD13Q1 (250m resolution). "
            "Sentinel-2 (10m) will be available after Copernicus credentials are configured."
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"NDVI analysis failed: {str(e)}",
        )
