from fastapi import APIRouter, HTTPException
from services.location_service import get_location
from services.weather_service import get_forecast
from services.alerts_service import check_alerts

router = APIRouter()


@router.get("/alerts")
def alerts(city: str):
    location = get_location(city)
    if location is None:
        raise HTTPException(status_code=404, detail="City not found")

    forecast = get_forecast(location["latitude"], location["longitude"])
    active_alerts = check_alerts(forecast)

    return {**location, "alerts": active_alerts}
