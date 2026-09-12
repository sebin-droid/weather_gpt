from fastapi import APIRouter, HTTPException

from services.nlp_service import understand_query
from services.location_service import get_location
from services.weather_service import get_current_weather, get_forecast
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

    return (
        f"In {city}, the current condition is {weather_data['condition']}, "
        f"the temperature is {weather_data['temperature']} C, humidity is "
        f"{weather_data['humidity']}%, precipitation is {weather_data['precipitation']} mm, "
        f"and wind speed is {weather_data['wind_speed']} km/h."
    )


@router.get("/chat")
def chat(question: str, lang: str = "en"):
    processed_question = question
    query = understand_query(processed_question)

    # Step 3: Handle missing city (with translated response)
    if query["location"] is None:
        msg = "Please mention a city name."
        if lang != "en":
            msg = translate_text(msg, target_lang=lang)
        return {"question": question, "message": msg}

    # Step 4: Lookup location
    location = get_location(query["location"])
    if location is None:
        err_msg = "City not found"
        if lang != "en":
            err_msg = translate_text(err_msg, target_lang=lang)
        raise HTTPException(status_code=404, detail=err_msg)

    # Step 5: Fetch forecast or current weather
    if query["intent"] == "forecast":
        weather_data = get_forecast(location["latitude"], location["longitude"])
    else:
        weather_data = get_current_weather(location["latitude"], location["longitude"])

    # Step 6: Construct answer and translate it back to user's selected language
    answer_text = make_answer(query, weather_data, location["city"], processed_question)

    if lang != "en" and answer_text:
        answer_text = translate_text(answer_text, target_lang=lang)

    return {
        "question": question,
        "location": location,
        "intent": query["intent"],
        "answer_text": answer_text,
        "data": weather_data
    }