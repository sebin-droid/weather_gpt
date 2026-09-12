from fastapi import APIRouter, HTTPException

from services.location_service import get_location
from services.weather_service import get_forecast
from services.alerts_service import check_alerts


router = APIRouter()


# --------------------------------------------------
# ACTIVE WEATHER ALERTS BY CITY
# --------------------------------------------------

@router.get("/alerts")
def alerts(city: str):
    """
    Checks the 7-day forecast for a city and returns a list of
    active weather warnings (heavy rain, high wind, heatwave).
    Returns an empty list if conditions are normal.
    """

    location = get_location(city)

    if location is None:
        raise HTTPException(status_code=404, detail="City not found")

    try:
        forecast_data = get_forecast(
            location["latitude"],
            location["longitude"]
        )

        active_alerts = check_alerts(forecast_data)

        return {
            **location,
            "alert_count": len(active_alerts),
            "alerts": active_alerts
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
