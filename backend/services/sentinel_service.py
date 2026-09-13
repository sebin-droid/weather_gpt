"""
sentinel_service.py — Sentinel-2 Scene Discovery via Copernicus STAC API

Provides satellite observation availability for user-drawn polygons.
Uses the FREE Copernicus Data Space STAC endpoint (no authentication needed for search).

Phase 1: Scene search + availability calendar data
Phase 2: Will add band download + NDVI calculation with OIDC auth
"""

import requests
from datetime import datetime, timedelta


STAC_SEARCH_URL = "https://catalogue.dataspace.copernicus.eu/stac/search"
COLLECTION = "sentinel-2-l2a"


def classify_cloud_quality(cloud_cover_pct):
    """
    Classify scene quality based on cloud cover percentage.
    Returns (quality_label, usable_bool).
    """
    if cloud_cover_pct is None:
        return "unknown", False
    if cloud_cover_pct < 30:
        return "good", True
    elif cloud_cover_pct < 60:
        return "limited", True
    else:
        return "poor", False


def polygon_to_bbox(polygon_coords):
    """
    Convert [[lat, lon], ...] polygon to [west, south, east, north] bbox.
    STAC expects [lon_min, lat_min, lon_max, lat_max].
    """
    lats = [p[0] for p in polygon_coords]
    lons = [p[1] for p in polygon_coords]
    return [min(lons), min(lats), max(lons), max(lats)]


def search_sentinel2_scenes(polygon_coords, start_date, end_date):
    """
    Search Copernicus STAC for Sentinel-2 L2A scenes intersecting the polygon's bbox.

    Args:
        polygon_coords: [[lat, lon], ...] — user's polygon
        start_date: "YYYY-MM-DD" — search window start
        end_date: "YYYY-MM-DD" — search window end

    Returns:
        List of observation dicts:
        [{
            "date": "2026-09-04",
            "source": "sentinel-2",
            "satellite": "Sentinel-2C",
            "cloud_cover_pct": 21.24,
            "quality": "good",
            "usable": True,
            "scene_id": "S2C_MSIL2A_...",
            "tile": "43PFM",
            "resolution": "10m"
        }]
    """
    bbox = polygon_to_bbox(polygon_coords)

    # Format dates for STAC
    dt_start = f"{start_date}T00:00:00Z"
    dt_end = f"{end_date}T23:59:59Z"

    try:
        response = requests.post(
            STAC_SEARCH_URL,
            json={
                "collections": [COLLECTION],
                "bbox": bbox,
                "datetime": f"{dt_start}/{dt_end}",
                "limit": 100,
            },
            headers={"Content-Type": "application/json"},
            timeout=20,
        )

        if response.status_code != 200:
            print(f"STAC search error: {response.status_code} - {response.text[:200]}")
            return []

        data = response.json()
        features = data.get("features", [])

        observations = []
        seen_dates = set()  # Deduplicate by date (multiple tiles per date)

        for feat in features:
            props = feat.get("properties", {})
            dt_str = props.get("datetime", "")[:10]
            cloud = props.get("eo:cloud_cover")
            tile = props.get("grid:code", "")
            if tile.startswith("MGRS-"):
                tile = tile[5:]

            # Extract satellite name from scene ID
            scene_id = feat.get("id", "")
            if scene_id.startswith("S2A"):
                satellite = "Sentinel-2A"
            elif scene_id.startswith("S2B"):
                satellite = "Sentinel-2B"
            elif scene_id.startswith("S2C"):
                satellite = "Sentinel-2C"
            else:
                satellite = "Sentinel-2"

            quality, usable = classify_cloud_quality(cloud)

            # For the same date, keep the scene with lowest cloud cover
            date_key = dt_str
            if date_key in seen_dates:
                # Check if this scene has lower cloud cover
                existing = next(
                    (o for o in observations if o["date"] == dt_str), None
                )
                if existing and cloud is not None:
                    if cloud < existing["cloud_cover_pct"]:
                        existing["cloud_cover_pct"] = round(cloud, 1)
                        existing["quality"] = quality
                        existing["usable"] = usable
                        existing["scene_id"] = scene_id
                        existing["satellite"] = satellite
                        existing["tile"] = tile
                continue

            seen_dates.add(date_key)
            observations.append({
                "date": dt_str,
                "source": "sentinel-2",
                "satellite": satellite,
                "cloud_cover_pct": round(cloud, 1) if cloud is not None else None,
                "quality": quality,
                "usable": usable,
                "scene_id": scene_id,
                "tile": tile,
                "resolution": "10m",
            })

        # Sort by date descending (newest first)
        observations.sort(key=lambda x: x["date"], reverse=True)
        return observations

    except requests.RequestException as e:
        print(f"Sentinel-2 STAC search failed: {e}")
        return []
    except Exception as e:
        print(f"Sentinel-2 search error: {e}")
        return []
