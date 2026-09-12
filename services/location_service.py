import requests


def get_location(city: str):
    """
    Convert a city name into geographic coordinates (latitude + longitude).

    This is called "geocoding" -- turning a human-readable place name
    into numbers that a map or weather API can use.

    We use the Open-Meteo Geocoding API, which is completely FREE and
    requires NO API key. Just send a city name, get back coordinates.

    Parameters:
        city (str): The name of the city to look up, e.g. "Kochi" or "Delhi"

    Returns:
        dict: A dictionary with city, country, latitude, longitude
              Returns None if the city is not found or the input is blank.
    """

    # .strip() removes any extra spaces the user might have typed
    # e.g. "  Kochi  " becomes "Kochi"
    city = city.strip()

    # If the city name is empty after stripping, return None immediately
    # This prevents sending a useless request to the API
    if not city:
        return None

    # The URL of the Open-Meteo Geocoding API
    url = "https://geocoding-api.open-meteo.com/v1/search"

    # "params" are the questions we're passing to the API
    # name: the city name to search for
    # count: 1 means "give me only the top result" (best match)
    # language: "en" means return city/country names in English
    params = {
        "name": city,
        "count": 1,
        "language": "en"
    }

    # Actually send the HTTP GET request to the API
    response = requests.get(url, params=params)

    # .raise_for_status() will throw an error if the API returned an error code
    response.raise_for_status()

    # .json() converts the API's text response into a Python dictionary
    data = response.json()

    # The API returns a key called "results" with a list of matching cities
    results = data.get("results")
    if not results:
        return None

    # Take the first (and best) result from the list
    place = results[0]

    # Build and return our own clean dictionary with just the fields we need
    return {
        "city": place["name"],
        "country": place.get("country", ""),
        "latitude": place["latitude"],
        "longitude": place["longitude"]
    }
