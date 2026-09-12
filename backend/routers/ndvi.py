from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta

from services.ndvi_service import analyze_ndvi, calculate_polygon_area


router = APIRouter()


class NDVIRequest(BaseModel):
    polygon: List[List[float]]  # [[lat1, lon1], [lat2, lon2], ...]
    date: Optional[str] = None  # YYYY-MM-DD, defaults to ~10 days ago


@router.post("/ndvi/analyze")
def ndvi_analyze(request: NDVIRequest):
    """
    Analyze vegetation health (NDVI) for a user-drawn polygon.
    Uses real MODIS satellite data — no fake values.
    """

    if not request.polygon or len(request.polygon) < 3:
        raise HTTPException(
            status_code=400,
            detail="Polygon must have at least 3 points.",
        )

    # Check polygon area isn't too large
    area = calculate_polygon_area(request.polygon)
    if area > 10000:
        raise HTTPException(
            status_code=400,
            detail=f"Polygon too large ({area:.0f} ha). Maximum is 10,000 hectares.",
        )

    # Default date: ~10 days ago (MODIS has processing lag)
    target_date = request.date
    if not target_date:
        target_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

    try:
        result = analyze_ndvi(request.polygon, target_date)

        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"NDVI analysis failed: {str(e)}",
        )
