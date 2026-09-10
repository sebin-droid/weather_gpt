from fastapi import FastAPI, HTTPException

from services.location_service import get_location
from services.weather_service import (
    get_current_weather,
    get_forecast
)


app = FastAPI(
    title="WeatherGPT API",
    description="AI-powered weather intelligence backend",
    version="1.0.0"
)


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.get("/")
def home():

    return {
        "message": "WeatherGPT Backend is Running!"
    }


# --------------------------------------------------
# CURRENT WEATHER BY COORDINATES
# --------------------------------------------------

@app.get("/weather")
def weather(latitude: float, longitude: float):

    try:

        weather_data = get_current_weather(
            latitude,
            longitude
        )

        return {
            "latitude": latitude,
            "longitude": longitude,
            "weather": weather_data
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# --------------------------------------------------
# CURRENT WEATHER BY CITY
# --------------------------------------------------

@app.get("/weather/city")
def weather_by_city(city: str):

    location = get_location(city)

    if location is None:

        raise HTTPException(
            status_code=404,
            detail="City not found"
        )

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

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# --------------------------------------------------
# 7-DAY FORECAST BY CITY
# --------------------------------------------------

@app.get("/forecast")
def forecast(city: str):

    location = get_location(city)

    if location is None:

        raise HTTPException(
            status_code=404,
            detail="City not found"
        )

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

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )