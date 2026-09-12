import requests


def get_location(city: str):
    """
    Convert a city name to geographic coordinates using the
    free Open-Meteo Geocoding API (no API key needed).

    Parameters:
        city (str): City name, e.g. "Kochi" or "Delhi"

    Returns:
        dict with city, country, latitude, longitude — or None if not found.
    """
    city = city.strip()
    if not city:
        return None

    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": city, "count": 1, "language": "en"}

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    results = data.get("results")
    if not results:
        return None

    place = results[0]
    return {
        "city": place["name"],
        "country": place.get("country", ""),
        "latitude": place["latitude"],
        "longitude": place["longitude"]
    }
