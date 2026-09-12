from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Routers
from routers.chat import router as chat_router
from routers.weather import router as weather_router
from routers.alerts import router as alerts_router
from routers.location import router as location_router
from routers.translate import router as translate_router
from routers.speech import router as speech_router
from routers.route import router as route_router
from routers.boundary import router as boundary_router
from routers.ndvi import router as ndvi_router

# Services
from services.location_service import get_location
from services.weather_service import (
    get_current_weather,
    get_forecast
)

app = FastAPI(
    title="WeatherGPT API",
    description="AI-powered weather intelligence backend",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers exactly ONCE
app.include_router(chat_router)
app.include_router(weather_router)
app.include_router(alerts_router)
app.include_router(location_router)
app.include_router(translate_router)
app.include_router(speech_router)
app.include_router(route_router)
app.include_router(boundary_router)
app.include_router(ndvi_router)


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "WeatherGPT Backend is Running!"
    }


# --------------------------------------------------
# CURRENT WEATHER USING COORDINATES
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
# CURRENT WEATHER USING CITY NAME
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
# 7 DAY FORECAST
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
