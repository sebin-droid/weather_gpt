from fastapi import APIRouter, HTTPException

from services.location_service import get_location

# APIRouter is like a mini-app that groups related endpoints together.
# Instead of putting everything in main.py, we organize by feature:
# - location.py handles anything about searching cities
# - weather.py (Person 3) handles weather data
# - chat.py (Person 1) handles the AI chat
# Person 1 will connect all routers in main.py using app.include_router()
router = APIRouter()


@router.get("/location/search")
def location_search(q: str):
    """
    Search for a city by name and return its coordinates.

    This creates a GET endpoint at:
        http://127.0.0.1:8000/location/search?q=kochi

    The "q" parameter is the city name the user is searching for.
    The "?" in the URL means "query parameter" -- it's how you pass data
    in a GET request, like filling in a search box on Google.

    What happens when someone visits this URL:
    1. FastAPI reads the "q" value from the URL (e.g., "kochi")
    2. We pass it to get_location() which calls the geocoding API
    3. If found, we return a JSON dict with city, country, lat, lon
    4. If NOT found, we raise HTTP 404 (the same "not found" error you
       see in browsers when a webpage doesn't exist)
    """

    # Call our location service to look up the city
    location = get_location(q)

    # If the city wasn't found, raise a 404 error
    # HTTP 404 = "Not Found" -- the standard web code for "doesn't exist"
    # FastAPI will automatically format this as a proper JSON error response
    if location is None:
        raise HTTPException(
            status_code=404,
            detail="Location not found"
        )

    # If we get here, location was found -- just return it as JSON
    # FastAPI automatically converts a Python dict to a JSON response
    return location
