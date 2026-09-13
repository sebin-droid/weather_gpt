"""
chat.py  —  WeatherGPT chat router
------------------------------------
Endpoints:
  POST /chat   { question, lang, history }   ← primary (with conversation context)
  GET  /chat?question=...&lang=...            ← backward-compatible wrapper

Flow (POST):
  1. _classify_message()            — greetings, thanks, chit-chat
  2. resolve_conversation_context() — follow-up detection + location/intent/time inheritance
  3. Reuse previous weather data OR fetch fresh data
  4. make_friendly_answer()          — Qwen3-8B → Groq fallback
  5. _template_answer()              — last resort if both LLMs unavailable
"""

from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.context_service import resolve_conversation_context
from services.location_service import get_location
from services.weather_service import get_current_weather, get_forecast
from services.translation_service import translate_text
from services.llm_service import make_friendly_answer, _call_llm

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class HistoryMessage(BaseModel):
    role: str
    content: str
    location: Optional[str] = None
    weather_data: Optional[Any] = None   # dict (current) OR list (forecast)
    context: Optional[Any] = None


class ChatRequest(BaseModel):
    question: str
    lang: str = "en"
    history: list[HistoryMessage] = []


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
    "what is weathergpt", "tell me about yourself", "what do you do",
    "what are your capabilities", "how do you work",
}

_FAREWELLS = {"bye", "goodbye", "see you", "cya", "take care", "later", "good bye"}

# These ALWAYS pass through to weather/context handling — never caught as chit-chat
_PASSTHROUGH = {
    "more", "tell more", "tell me more", "elaborate", "explain", "describe",
    "describe more", "details", "more details", "what else", "anything else",
    "more info", "more information", "why", "how", "and humidity", "and wind",
    "and temperature", "and rain", "and forecast", "tomorrow", "tonight",
    "next week", "weekend", "what about tomorrow", "how about tomorrow",
    "will it rain", "is it hot", "is it cold", "is it windy", "is it humid",
    "compare", "compare with tomorrow", "show me more", "tell me",
    "the situation", "situation", "umbrella", "travel", "go out", "outside",
}


def _classify_message(text: str) -> str | None:
    """Returns chit-chat category or None (pass through to weather/context)."""
    t = text.lower().strip().rstrip("!.,?")

    # Pass-through: these go straight to context resolution
    if t in _PASSTHROUGH or any(t.startswith(p) for p in _PASSTHROUGH):
        return None

    if t in _GREETINGS or any(t.startswith(g) for g in _GREETINGS):
        return "greeting"
    if t in _THANKS:
        return "thanks"
    if t in _FAREWELLS:
        return "farewell"
    if t in _ABOUT or any(t == a or t.startswith(a) for a in _ABOUT):
        return "about"

    # Very short messages with no weather keywords → chit-chat
    weather_hints = {
        "weather", "rain", "temperature", "wind", "humidity", "forecast",
        "hot", "cold", "sunny", "cloudy", "storm", "flood", "snow", "climate",
        "more", "tell", "describe", "tomorrow", "today", "week", "outside",
        "umbrella", "travel",
    }
    words = set(t.split())
    if len(words) <= 2 and not words.intersection(weather_hints):
        return "chit-chat"
    return None


def _small_talk_reply(category: str, question: str, lang: str) -> str:
    """Generate a warm reply for non-weather messages (LLM or canned)."""
    canned = {
        "greeting": (
            "👋 Hello! I'm WeatherGPT — your AI weather assistant. "
            "Ask me about the weather, rain, temperature, or forecasts for any city! "
            "Try: 'Will it rain in Mumbai tomorrow?'"
        ),
        "thanks": "😊 You're welcome! Feel free to ask me anything about the weather.",
        "farewell": "👋 Goodbye! Stay weather-safe out there!",
        "about": (
            "🌦️ I'm WeatherGPT — an AI-powered weather assistant. "
            "I can tell you current weather conditions, rainfall forecasts, temperature, "
            "wind speed, humidity, and travel advice for cities across India and the world. "
            "Just ask naturally — no need for specific commands!"
        ),
        "chit-chat": (
            "😊 I'm WeatherGPT, specialised in weather! "
            "Try: 'What's the weather in Bangalore?' or 'Will it rain in Delhi tomorrow?'"
        ),
    }
    system = (
        "You are WeatherGPT, a friendly AI weather assistant. "
        "The user sent a non-weather message. Reply warmly in 1-2 sentences, "
        "introduce yourself if needed, and guide them to ask a weather question. "
        f"Respond in the language with ISO code '{lang}'."
    )
    llm_reply = _call_llm(
        [{"role": "system", "content": system}, {"role": "user", "content": question}],
        max_tokens=120,
        temperature=0.4,
    )
    if llm_reply:
        return llm_reply.strip()
    reply = canned.get(category, canned["chit-chat"])
    if lang != "en":
        try:
            reply = translate_text(reply, target_lang=lang)
        except Exception:
            pass
    return reply


# ---------------------------------------------------------------------------
# Template answer fallback (used when BOTH LLMs are unavailable)
# ---------------------------------------------------------------------------

def _template_answer(
    intent: str,
    weather_variable: str,
    time: str,
    weather_data: Any,
    city: str,
) -> str:
    """Human-friendly template answers — last resort when LLMs are down."""

    # Forecast
    if intent == "forecast" and isinstance(weather_data, list) and weather_data:
        if time == "tomorrow" and len(weather_data) > 1:
            day = weather_data[1]
        elif time in ("weekend",) and len(weather_data) > 5:
            day = weather_data[5]
        else:
            day = weather_data[0]
        rain_mm = day.get("rain", 0) or 0
        rain_str = f"{rain_mm} mm of rain expected" if rain_mm > 0 else "no rain expected"
        return (
            f"In {city} on {day['date']}: {day['condition']}, "
            f"temperatures {day['min_temperature']}–{day['max_temperature']} °C, {rain_str}."
        )

    # Current weather
    if not isinstance(weather_data, dict):
        return f"Weather data for {city} is unavailable right now."

    temp = weather_data.get("temperature", "?")
    humidity = weather_data.get("humidity", "?")
    wind = weather_data.get("wind_speed", "?")
    precip = weather_data.get("precipitation", 0) or 0
    condition = weather_data.get("condition", "")

    if weather_variable == "temperature":
        return f"It is currently {temp} °C in {city} ({condition})."
    if weather_variable == "rain":
        if precip == 0:
            return f"It is not currently raining in {city} (0 mm precipitation)."
        return f"It is raining in {city} — current precipitation is {precip} mm."
    if weather_variable == "wind":
        return f"The wind speed in {city} is currently {wind} km/h."
    if weather_variable == "humidity":
        return f"The humidity in {city} is currently {humidity}%."

    rain_str = f"{precip} mm precipitation" if precip > 0 else "no precipitation"
    return (
        f"In {city}: {condition}, {temp} °C, "
        f"humidity {humidity}%, {rain_str}, wind {wind} km/h."
    )


# ---------------------------------------------------------------------------
# Core chat logic (shared by both GET and POST endpoints)
# ---------------------------------------------------------------------------

def _process_chat(question: str, lang: str, history: list[dict]) -> dict[str, Any]:
    """
    Main chat handler. Returns a JSON-serialisable response dict.

    Steps:
      0. Greeting / chit-chat check
      1. Resolve full conversation context
      2. Handle missing location gracefully
      3. Geocode city
      4. Decide: reuse previous weather data OR fetch fresh
      5. Generate LLM answer (Qwen → Groq → template fallback)
    """

    # Step 0 — Greetings / small-talk
    category = _classify_message(question)
    if category:
        reply = _small_talk_reply(category, question, lang)
        return {"question": question, "answer_text": reply, "intent": category}

    # Step 1 — Resolve conversation context
    ctx = resolve_conversation_context(question, lang, history)

    # Step 2 — Handle missing location
    if ctx.resolved_location is None:
        if ctx.is_follow_up:
            msg = "Which city or area are you asking about?"
        else:
            msg = (
                "I couldn't find a city name in your question. "
                "Try: 'What's the weather in Mumbai?' or 'Will it rain in Delhi tomorrow?'"
            )
        if lang != "en":
            try:
                msg = translate_text(msg, target_lang=lang)
            except Exception:
                pass
        return {"question": question, "answer_text": msg, "intent": "unknown"}

    # Step 3 — Geocode
    location = get_location(ctx.resolved_location)
    if location is None:
        err_msg = (
            f"Sorry, I couldn't find weather data for '{ctx.resolved_location}'. "
            "Please check the city name."
        )
        if lang != "en":
            try:
                err_msg = translate_text(err_msg, target_lang=lang)
            except Exception:
                pass
        raise HTTPException(status_code=404, detail=err_msg)

    city = location["city"]

    # Step 4 — Fetch weather data
    # For follow-ups that inherit a "forecast" intent, always fetch forecast.
    # For "describe more" after a forecast question, we already have previous
    # forecast data — but fetching fresh is fine and keeps data up-to-date.
    if ctx.intent == "forecast":
        weather_data = get_forecast(location["latitude"], location["longitude"])
    else:
        weather_data = get_current_weather(location["latitude"], location["longitude"])

    # Step 5 — Generate answer
    answer_text = make_friendly_answer(
        weather_data=weather_data,
        city=city,
        question=question,
        lang=lang,
        intent=ctx.intent,
        time=ctx.time,
        history=history,
        is_follow_up=ctx.is_follow_up,
    )

    # Template fallback if both LLMs are unavailable
    if not answer_text:
        answer_text = _template_answer(
            intent=ctx.intent,
            weather_variable=ctx.weather_variable,
            time=ctx.time,
            weather_data=weather_data,
            city=city,
        )
        if lang != "en":
            try:
                answer_text = translate_text(answer_text, target_lang=lang)
            except Exception:
                pass

    # Build response
    response = {
        "question": question,
        "location": location,
        "intent": ctx.intent,
        "is_follow_up": ctx.is_follow_up,
        "answer_text": answer_text,
        "data": weather_data,
        # Metadata stored in history by the frontend for context resolution
        "_ctx": {
            "location": city,
            "intent": ctx.intent,
            "weather_variable": ctx.weather_variable,
            "time": ctx.time,
        },
    }
    return response


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/chat")
def chat_post(body: ChatRequest):
    """Primary endpoint. Accepts { question, lang, history[] } as JSON."""
    history = [h.model_dump() for h in body.history]
    return _process_chat(body.question, body.lang, history)


@router.get("/chat")
def chat_get(question: str, lang: str = "en"):
    """Backward-compatible GET endpoint — no history context."""
    return _process_chat(question, lang, [])