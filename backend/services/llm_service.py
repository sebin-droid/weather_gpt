import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# llama-3.1-8b-instant: fast, multilingual, instruction-tuned — much better
# than allam-2-7b (Arabic-focused) for Indian English and code-switched queries.
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

    Returns a dict like:
        {
            "intent": "forecast" | "rain" | "temperature" | "wind" | "humidity" | "current_weather",
            "location": "Mumbai" | null,
            "time": "now" | "today" | "tomorrow" | "next_week" | "tonight" | "weekend",
            "weather_variable": "rain" | "temperature" | "wind" | "humidity" | "general"
        }
    Returns None if the LLM is unavailable or returns unparseable output.
    """
    system_prompt = (
        "You are a weather query parser. Extract structured information from a user's weather question.\n"
        "Return ONLY a valid JSON object with exactly these keys:\n"
        "  - intent: one of [forecast, rain, temperature, wind, humidity, current_weather]\n"
        "  - location: the city/place name as a properly capitalised string, or null if not mentioned\n"
        "  - time: one of [now, today, tonight, tomorrow, weekend, next_week]\n"
        "  - weather_variable: one of [rain, temperature, wind, humidity, general]\n\n"
        "Rules:\n"
        "- If the user asks about forecast / next few days / this week → intent=forecast\n"
        "- If the user asks about rain/drizzle/pour/storm/flood → intent=rain, weather_variable=rain\n"
        "- If the user asks about temperature/hot/cold/heat/feels like → intent=temperature, weather_variable=temperature\n"
        "- If the user asks about wind → intent=wind, weather_variable=wind\n"
        "- If the user asks about humidity/muggy/damp → intent=humidity, weather_variable=humidity\n"
        "- Otherwise → intent=current_weather, weather_variable=general\n"
        "- The question may be in Hindi, Tamil, Telugu, Bengali, Malayalam, or any Indian language — extract accordingly.\n"
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
        # Validate required keys are present
        required = {"intent", "location", "time", "weather_variable"}
        if required.issubset(parsed.keys()):
            return parsed
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def make_friendly_answer(weather_data: dict, city: str, question: str, lang: str = "en") -> str | None:
    """
    Generate a natural, conversational answer given weather data.

    If lang is not English, instructs the LLM to respond in that language directly,
    avoiding the need for a separate translation step.
    """
    lang_instruction = (
        f"Respond in the language with ISO code '{lang}'."
        if lang != "en"
        else "Respond in English."
    )

    prompt = (
        f"The user asked: '{question}'\n"
        f"Here is the live weather data for {city}: {json.dumps(weather_data, ensure_ascii=False)}\n"
        f"Write one short, friendly, conversational sentence answering their question using this data. "
        f"Include the city name and relevant numbers. {lang_instruction}"
    )
    messages = [{"role": "user", "content": prompt}]
    answer = _call_groq(messages, max_tokens=200)
    if answer:
        return answer.strip()
    return None