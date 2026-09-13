from fastapi import APIRouter, HTTPException

from services.nlp_service import understand_query
from services.location_service import get_location
from services.weather_service import get_current_weather, get_forecast
from services.translation_service import translate_text
from services.llm_service import make_friendly_answer, _call_groq

router = APIRouter()


# ---------------------------------------------------------------------------
# Greeting / small-talk detection
# ---------------------------------------------------------------------------

_GREETINGS = {
    "hi", "hello", "hey", "hii", "helo", "hola", "howdy", "greetings",
    "good morning", "good afternoon", "good evening", "good night",
    "what's up", "whats up", "sup", "yo",
}

_THANKS = {
    "thanks", "thank you", "thank you so much", "thx", "ty",
    "great", "awesome", "nice", "cool", "perfect", "ok", "okay", "got it",
}

_ABOUT = {
    "who are you", "what are you", "what can you do", "help",
    "what is weathergpt", "tell me about yourself",
}

_FAREWELLS = {"bye", "goodbye", "see you", "cya", "take care", "later"}

# Follow-up phrases that should pass through to weather NLP, not be caught as chit-chat
_FOLLOWUP_HINTS = {
    "more", "tell more", "tell me more", "elaborate", "explain",
    "details", "more details", "what else", "and what", "anything else",
    "more info", "more information", "give more", "more about",
    "expand", "brief me", "brief", "summary", "summarize",
}


def _classify_message(text: str) -> str | None:
    """
    Returns a pre-canned category if the message is clearly a greeting /
    small-talk / off-topic query, otherwise returns None (proceed to NLP).
    """
    t = text.lower().strip().rstrip("!.,?")

    # Never intercept follow-up/elaboration requests — let NLP handle them
    if t in _FOLLOWUP_HINTS or any(t.startswith(h) for h in _FOLLOWUP_HINTS):
        return None

    if t in _GREETINGS or any(t.startswith(g) for g in _GREETINGS):
        return "greeting"
    if t in _THANKS:
        return "thanks"
    if t in _FAREWELLS:
        return "farewell"
    if t in _ABOUT or any(t in a for a in _ABOUT):
        return "about"
    # Very short messages with no weather keywords — likely chit-chat
    weather_hints = {
        "weather", "rain", "temperature", "wind", "humidity", "forecast",
        "hot", "cold", "sunny", "cloudy", "storm", "flood", "snow", "climate",
        "city", "today", "tomorrow", "week", "more", "tell",
    }
    words = set(t.split())
    if len(words) <= 3 and not words.intersection(weather_hints):
        return "chit-chat"
    return None


def _small_talk_reply(category: str, question: str, lang: str) -> str:
    """
    Generate a friendly reply for non-weather messages.
    Tries the LLM first for a natural response; falls back to a canned reply.
    """
    canned = {
        "greeting": (
            "👋 Hello! I'm WeatherGPT — your AI weather assistant. "
            "Ask me about the weather, rain, temperature, or forecasts for any city! "
            "Try: *'Will it rain in Mumbai tomorrow?'*"
        ),
        "thanks": "😊 You're welcome! Feel free to ask me anything about the weather.",
        "farewell": "👋 Goodbye! Stay weather-safe out there!",
        "about": (
            "🌦️ I'm WeatherGPT — an AI-powered weather assistant. "
            "I can tell you about current weather, rain forecasts, temperature, wind, humidity, "
            "and more for cities across India and the world. Just ask!"
        ),
        "chit-chat": (
            "😊 I'm WeatherGPT, specialised in weather! "
            "Try asking: *'What's the weather in Bangalore?'* or *'Will it rain in Delhi tomorrow?'*"
        ),
    }

    # Try LLM for a warm, contextual response
    system = (
        "You are WeatherGPT, a friendly AI weather assistant. "
        "The user sent a non-weather message. Reply warmly in 1-2 sentences, "
        "introduce yourself briefly if needed, and gently guide them to ask a weather question. "
        f"Respond in the language with ISO code '{lang}'."
    )
    llm_reply = _call_groq(
        [{"role": "system", "content": system}, {"role": "user", "content": question}],
        max_tokens=120,
    )
    if llm_reply:
        return llm_reply.strip()

    reply = canned.get(category, canned["chit-chat"])
    if lang != "en":
        reply = translate_text(reply, target_lang=lang)
    return reply


def _template_answer(query: dict, weather_data: dict, city: str) -> str:
    """
    Rule-based template answer used as a final fallback when the LLM is
    unavailable. Uses human-friendly language instead of raw numbers.
    """
    if query["intent"] == "forecast":
        if query["time"] == "tomorrow" and len(weather_data) > 1:
            day = weather_data[1]
        elif query["time"] == "weekend" and len(weather_data) > 5:
            day = weather_data[5]
        else:
            day = weather_data[0]

        rain_mm = day.get("rain", 0) or 0
        rain_str = f"{rain_mm} mm of rain expected" if rain_mm > 0 else "no rain expected"
        return (
            f"In {city} on {day['date']}: {day['condition']}, "
            f"temperatures {day['min_temperature']}–{day['max_temperature']} °C, {rain_str}."
        )

    if query["weather_variable"] == "temperature":
        temp = weather_data.get("temperature", "?")
        condition = weather_data.get("condition", "")
        return f"It is currently {temp} °C in {city} ({condition})."

    if query["weather_variable"] == "rain":
        precip = weather_data.get("precipitation", 0) or 0
        if precip == 0:
            return f"It is not currently raining in {city} (precipitation: 0 mm)."
        return f"It is raining in {city} — current precipitation is {precip} mm."

    if query["weather_variable"] == "wind":
        return f"The wind speed in {city} is currently {weather_data.get('wind_speed', '?')} km/h."

    if query["weather_variable"] == "humidity":
        return f"The humidity in {city} is currently {weather_data.get('humidity', '?')}%."

    # General / current_weather
    precip = weather_data.get("precipitation", 0) or 0
    rain_str = f"{precip} mm precipitation" if precip > 0 else "no precipitation"
    return (
        f"In {city}: {weather_data.get('condition', 'N/A')}, "
        f"{weather_data.get('temperature', '?')} °C, "
        f"humidity {weather_data.get('humidity', '?')}%, "
        f"{rain_str}, wind {weather_data.get('wind_speed', '?')} km/h."
    )


@router.get("/chat")
def chat(question: str, lang: str = "en"):
    # Step 0: Handle greetings, thanks, and off-topic messages gracefully
    category = _classify_message(question)
    if category:
        reply = _small_talk_reply(category, question, lang)
        return {"question": question, "answer_text": reply, "intent": category}

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
        intent=query["intent"],
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