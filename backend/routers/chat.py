from fastapi import APIRouter, HTTPException

from services.nlp_service import understand_query
from services.location_service import get_location
from services.weather_service import get_current_weather, get_forecast
from services.translation_service import translate_text
from services.llm_service import make_friendly_answer

router = APIRouter()


def _template_answer(query: dict, weather_data: dict, city: str) -> str:
    """
    Rule-based template answer used as a final fallback when the LLM is
    unavailable AND translation has already been applied upstream.
    """
    if query["intent"] == "forecast":
        # For "tomorrow" pick index 1; for "weekend" pick index 5 (Sat); else index 0
        if query["time"] == "tomorrow" and len(weather_data) > 1:
            day = weather_data[1]
        elif query["time"] == "weekend" and len(weather_data) > 5:
            day = weather_data[5]
        else:
            day = weather_data[0]
        return (
            f"In {city} on {day['date']}, {day['condition']} is expected, "
            f"with temperatures from {day['min_temperature']} to "
            f"{day['max_temperature']} °C and {day['rain']} mm of rain."
        )

    if query["weather_variable"] == "temperature":
        return f"The current temperature in {city} is {weather_data['temperature']} °C."

    if query["weather_variable"] == "rain":
        return f"In {city}, current precipitation is {weather_data['precipitation']} mm."

    if query["weather_variable"] == "wind":
        return f"The current wind speed in {city} is {weather_data['wind_speed']} km/h."

    if query["weather_variable"] == "humidity":
        return f"The current humidity in {city} is {weather_data['humidity']}%."

    return (
        f"In {city}, the current condition is {weather_data['condition']}, "
        f"temperature is {weather_data['temperature']} °C, humidity is "
        f"{weather_data['humidity']}%, precipitation is {weather_data['precipitation']} mm, "
        f"and wind speed is {weather_data['wind_speed']} km/h."
    )


@router.get("/chat")
def chat(question: str, lang: str = "en"):
    # Step 1: Understand the query (LLM-first → regex fallback)
    query = understand_query(question)

    # Step 2: Handle missing city
    if query["location"] is None:
        msg = (
            "I couldn't find a city name in your question. "
            "Try asking: 'What's the weather in Mumbai?' or 'Will it rain in Delhi tomorrow?'"
        )
        if lang != "en":
            msg = translate_text(msg, target_lang=lang)
        return {"question": question, "message": msg}

    # Step 3: Resolve location coordinates
    location = get_location(query["location"])
    if location is None:
        err_msg = f"Sorry, I couldn't find weather data for '{query['location']}'. Please check the city name."
        if lang != "en":
            err_msg = translate_text(err_msg, target_lang=lang)
        raise HTTPException(status_code=404, detail=err_msg)

    # Step 4: Fetch weather data
    if query["intent"] == "forecast":
        weather_data = get_forecast(location["latitude"], location["longitude"])
    else:
        weather_data = get_current_weather(location["latitude"], location["longitude"])

    # Step 5: Generate answer
    # Prefer the LLM-generated friendly answer (it can respond in the user's
    # language directly, skipping the separate translation step).
    answer_text = make_friendly_answer(
        weather_data=weather_data,
        city=location["city"],
        question=question,
        lang=lang,
    )

    # Fall back to template answer if LLM is unavailable
    if not answer_text:
        answer_text = _template_answer(query, weather_data, location["city"])
        if lang != "en":
            answer_text = translate_text(answer_text, target_lang=lang)

    return {
        "question": question,
        "location": location,
        "intent": query["intent"],
        "nlp_source": query.get("source", "unknown"),
        "answer_text": answer_text,
        "data": weather_data,
    }