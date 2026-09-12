import requests
from datetime import date, timedelta


def get_climate_trend(latitude: float, longitude: float, days: int = 14):
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=days)

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"],
        "timezone": "auto"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()["daily"]

    trend = []
    for i in range(len(data["time"])):
        trend.append({
            "date": data["time"][i],
            "max_temp": data["temperature_2m_max"][i],
            "min_temp": data["temperature_2m_min"][i],
            "precipitation": data["precipitation_sum"][i]
        })
    return trend
