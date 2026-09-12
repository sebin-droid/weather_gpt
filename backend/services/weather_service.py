import requests

from utils.weather_codes import get_weather_description


def get_current_weather(latitude: float, longitude: float):

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "wind_speed_10m",
            "weather_code"
        ]
    }

    response = requests.get(url, params=params)

    response.raise_for_status()

    data = response.json()

    current = data["current"]

    return {
        "temperature": current["temperature_2m"],
        "humidity": current["relative_humidity_2m"],
        "precipitation": current["precipitation"],
        "wind_speed": current["wind_speed_10m"],
        "condition": get_weather_description(
            current["weather_code"]
        )
    }


def get_forecast(latitude: float, longitude: float):

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "rain_sum",
            "wind_speed_10m_max"
        ],
        "forecast_days": 7,
        "timezone": "auto"
    }

    response = requests.get(url, params=params)

    response.raise_for_status()

    data = response.json()

    daily = data["daily"]

    forecast = []

    for i in range(len(daily["time"])):

        day = {
            "date": daily["time"][i],

            "condition": get_weather_description(
                daily["weather_code"][i]
            ),

            "max_temperature": daily["temperature_2m_max"][i],

            "min_temperature": daily["temperature_2m_min"][i],

            "precipitation": daily["precipitation_sum"][i],

            "rain": daily["rain_sum"][i],

            "max_wind_speed": daily["wind_speed_10m_max"][i]
        }

        forecast.append(day)

    return forecast