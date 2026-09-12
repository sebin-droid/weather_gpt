from fastapi import APIRouter, HTTPException

from services.nlp_service import understand_query
from services.location_service import get_location
from services.weather_service import get_current_weather, get_forecast
from services.llm_service import make_friendly_answer
from services.translation_service import translate_text

router = APIRouter()


def make_answer(query: dict, weather_data: dict, city: str, question: str) -> str:
    if query["intent"] == "forecast":
        forecast_day = weather_data[1] if query["time"] == "tomorrow" else weather_data[0]
        return (
            f"In {city} on {forecast_day['date']}, {forecast_day['condition']} is expected, "
            f"with temperatures from {forecast_day['min_temperature']} to "
            f"{forecast_day['max_temperature']} C and {forecast_day['rain']} mm of rain."
        )

    if query["weather_variable"] == "temperature":
        return f"The current temperature in {city} is {weather_data['temperature']} C."

    if query["weather_variable"] == "rain":
        return f"In {city}, current precipitation is {weather_data['precipitation']} mm."

    if query["weather_variable"] == "wind":
        return f"The current wind speed in {city} is {weather_data['wind_speed']} km/h."

    if query["weather_variable"] == "humidity":
        return f"The current humidity in {city} is {weather_data['humidity']}%."

    return make_friendly_answer(weather_data, city, question)


@router.get("/chat")
def chat(question: str, lang: str = "en"):
    query = understand_query(question)

    if query["location"] is None:
        return {"question": question, "message": "Please mention a city name."}

    location = get_location(query["location"])
    if location is None:
        raise HTTPException(status_code=404, detail="City not found")

    if query["intent"] == "forecast":
        weather_data = get_forecast(location["latitude"], location["longitude"])
    else:
        weather_data = get_current_weather(location["latitude"], location["longitude"])

    answer_text = make_answer(query, weather_data, location["city"], question)

    answer_text = translate_text(answer_text, lang)

    return {
        "question": question,
        "location": location,
        "intent": query["intent"],
        "answer_text": answer_text,
        "data": weather_data
    }