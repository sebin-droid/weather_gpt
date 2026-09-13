"""
llm_service.py
--------------
LLM integration for WeatherGPT using Groq API.

Functions:
  _call_groq()             — low-level Groq API call
  extract_query_info()     — parse intent/location/time/variable from question
  build_llm_messages()     — construct message list with conversation history
  make_friendly_answer()   — generate a conversational weather answer
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# llama-3.1-8b-instant: fast, multilingual, instruction-tuned
DEFAULT_MODEL = "llama-3.1-8b-instant"


def _call_groq(messages: list, max_tokens: int = 200, json_mode: bool = False) -> str | None:
    """Low-level helper that calls the Groq API and returns the assistant message."""
    if not GROQ_API_KEY:
        return None
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        data: dict = {
            "model": DEFAULT_MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.4,
        }
        if json_mode:
            data["response_format"] = {"type": "json_object"}

        response = requests.post(GROQ_URL, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[LLM Error] {e}")
        return None


def extract_query_info(question: str) -> dict | None:
    """
    Ask the LLM to extract structured query information from a raw user question.

    Returns:
        { intent, location, time, weather_variable }
    or None if LLM unavailable.
    """
    system_prompt = (
        "You are a weather query parser. Extract structured information from a user's weather question.\n"
        "Return ONLY a valid JSON object with exactly these keys:\n"
        "  - intent: one of [forecast, rain, temperature, wind, humidity, current_weather]\n"
        "  - location: the city/place name as a properly capitalised string, or null if not mentioned\n"
        "  - time: one of [now, today, tonight, tomorrow, weekend, next_week]\n"
        "  - weather_variable: one of [rain, temperature, wind, humidity, general]\n\n"
        "Rules:\n"
        "- 'will it rain', 'is it going to rain', 'chance of rain', 'will there be rain' → intent=forecast, weather_variable=rain\n"
        "- 'is it raining', 'is it raining now', 'raining currently' → intent=rain, weather_variable=rain, time=now\n"
        "- forecast/next few days/this week/tomorrow/weekend → intent=forecast\n"
        "- rain/drizzle/pour/storm/flood/shower → weather_variable=rain\n"
        "- temperature/hot/cold/heat/feels like/chilly/warm → intent=temperature, weather_variable=temperature\n"
        "- wind/windy/breeze/gust → intent=wind, weather_variable=wind\n"
        "- humidity/muggy/damp/moisture → intent=humidity, weather_variable=humidity\n"
        "- Otherwise → intent=current_weather, weather_variable=general\n"
        "- The question may be in Hindi, Tamil, Telugu, Bengali, Malayalam, or any Indian language — extract accordingly.\n"
        "- For 'will it rain in <city>' with no time → time=today (not now)\n"
        "Return ONLY the JSON object, no explanation."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]
    raw = _call_groq(messages, max_tokens=120, json_mode=True)
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        required = {"intent", "location", "time", "weather_variable"}
        if required.issubset(parsed.keys()):
            return parsed
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def build_llm_messages(
    question: str,
    city: str,
    weather_data: dict,
    intent: str,
    lang: str,
    history: list[dict],
    is_follow_up: bool = False,
) -> list[dict]:
    """
    Build the messages array for the Groq chat completion call.

    Includes:
    - A rich system prompt with ground rules
    - Last N conversation turns (for context)
    - The current user question with weather data injected
    """
    lang_instruction = (
        f"Respond in the language with ISO code '{lang}'."
        if lang != "en"
        else "Respond in English."
    )

    system_prompt = (
        "You are WeatherGPT, a friendly, knowledgeable AI weather assistant.\n\n"
        "RULES:\n"
        "1. Answer naturally and conversationally — 2 to 4 sentences max.\n"
        "2. Use ONLY the weather data provided below. Do NOT invent or guess values.\n"
        "3. If precipitation is 0.0 mm → say it is not currently raining / no rain expected.\n"
        "4. If the user is asking a follow-up, use the previous conversation context.\n"
        "5. Do NOT ask for the city name if it is already clear from context.\n"
        "6. Do NOT mention internal system names like 'intent', 'context', 'FOLLOW_UP'.\n"
        "7. Do NOT say 'according to the context' or 'based on your previous question'.\n"
        "8. Do NOT repeat information the user just read unless they asked for it.\n"
        "9. Add a short practical tip where relevant (umbrella, hydration, etc.).\n"
        "10. For 'describe more' / 'tell me more' → give a richer 3-4 sentence summary.\n"
        f"11. {lang_instruction}\n\n"
        f"Current city: {city}\n"
        f"Current intent: {intent}\n"
        f"Live weather data: {json.dumps(weather_data, ensure_ascii=False)}"
    )

    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    # Inject last N conversation turns (for context window)
    # Use only content field from history; skip metadata fields
    for turn in history[-8:]:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    # Current question
    messages.append({"role": "user", "content": question})

    return messages


def make_friendly_answer(
    weather_data: dict,
    city: str,
    question: str,
    lang: str = "en",
    intent: str = "current_weather",
    history: list[dict] | None = None,
    is_follow_up: bool = False,
) -> str | None:
    """
    Generate a natural, conversational answer given weather data.

    Passes conversation history to the LLM for contextual responses.
    Falls back gracefully if the LLM is unavailable.
    """
    if history is None:
        history = []

    messages = build_llm_messages(
        question=question,
        city=city,
        weather_data=weather_data,
        intent=intent,
        lang=lang,
        history=history,
        is_follow_up=is_follow_up,
    )

    answer = _call_groq(messages, max_tokens=300)
    if answer:
        return answer.strip()
    return None