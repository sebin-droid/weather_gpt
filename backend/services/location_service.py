import requests


def get_location(city: str):
    city = city.strip()
    if not city:
        return None

    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": city, "count": 5, "language": "en"}

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    results = data.get("results")
    if not results:
        return None

    # Prefer Indian cities since this is an Indian weather app
    for place in results:
        if place.get("country_code") == "IN":
            return {
                "city": place["name"],
                "country": place.get("country", ""),
                "latitude": place["latitude"],
                "longitude": place["longitude"]
            }

    # Fallback to first result if no Indian match
    place = results[0]
    return {
        "city": place["name"],
        "country": place.get("country", ""),
        "latitude": place["latitude"],
        "longitude": place["longitude"]
    }