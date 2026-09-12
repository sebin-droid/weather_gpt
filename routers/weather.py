from fastapi import APIRouter, HTTPException

from services.location_service import get_location
from services.weather_service import get_current_weather, get_forecast
from services.climate_service import get_climate_trend


router = APIRouter()


# --------------------------------------------------
# CURRENT WEATHER BY CITY (via router)
# --------------------------------------------------

@router.get("/weather/current")
def weather_current(city: str):
    """Returns live current weather for any city."""

    location = get_location(city)

    if location is None:
        raise HTTPException(status_code=404, detail="City not found")

    try:
        weather_data = get_current_weather(
            location["latitude"],
            location["longitude"]
        )
        return {
            **location,
            "weather": weather_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# 7-DAY FORECAST BY CITY (via router)
# --------------------------------------------------

@router.get("/weather/forecast")
def weather_forecast(city: str):
    """Returns a 7-day daily forecast for any city."""

    location = get_location(city)

    if location is None:
        raise HTTPException(status_code=404, detail="City not found")

    try:
        forecast_data = get_forecast(
            location["latitude"],
            location["longitude"]
        )
        return {
            **location,
            "forecast": forecast_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------
# HISTORICAL CLIMATE TREND BY CITY
# --------------------------------------------------

@router.get("/climate/trend")
def climate_trend(city: str, days: int = 14):
    """
    Returns the last N days of historical weather data for a city.
    Default is 14 days. Max recommended: 30 days.
    """

    location = get_location(city)

    if location is None:
        raise HTTPException(status_code=404, detail="City not found")

    try:
        trend_data = get_climate_trend(
            location["latitude"],
            location["longitude"],
            days
        )
        return {
            **location,
            "days_requested": days,
            "trend": trend_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
