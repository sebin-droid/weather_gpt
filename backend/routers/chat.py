from fastapi import APIRouter, HTTPException

from services.nlp_service import understand_query
from services.location_service import get_location
from services.weather_service import get_current_weather, get_forecast
from services.llm_service import make_friendly_answer
from services.translation_service import translate_text

router = APIRouter()


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
        answer_text = f"Here is the forecast for {location['city']}."
    else:
        weather_data = get_current_weather(location["latitude"], location["longitude"])
        answer_text = make_friendly_answer(weather_data, location["city"], question)

    answer_text = translate_text(answer_text, lang)

    return {
        "question": question,
        "location": location,
        "intent": query["intent"],
        "answer_text": answer_text,
        "data": weather_data
    }