from fastapi import APIRouter, HTTPException
from services.location_service import get_location
from services.weather_service import get_current_weather, get_forecast
from services.climate_service import get_climate_trend

router = APIRouter()


@router.get("/weather/current")
def weather_current(city: str):
    location = get_location(city)
    if location is None:
        raise HTTPException(status_code=404, detail="City not found")
    return {**location, "weather": get_current_weather(location["latitude"], location["longitude"])}


@router.get("/weather/forecast")
def weather_forecast(city: str):
    location = get_location(city)
    if location is None:
        raise HTTPException(status_code=404, detail="City not found")
    return {**location, "forecast": get_forecast(location["latitude"], location["longitude"])}


@router.get("/climate/trend")
def climate_trend(city: str, days: int = 14):
    location = get_location(city)
    if location is None:
        raise HTTPException(status_code=404, detail="City not found")
    return {**location, "trend": get_climate_trend(location["latitude"], location["longitude"], days)}
