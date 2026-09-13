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


def make_friendly_answer(
    weather_data: dict,
    city: str,
    question: str,
    lang: str = "en",
    intent: str = "current_weather",
) -> str | None:
    """
    Generate a rich, natural, conversational answer given weather data.

    - Uses the full weather payload to give a complete picture.
    - Interprets numeric values into human language (e.g. 0.0mm = no rain).
    - Responds directly in the user's language when lang != 'en'.
    """
    lang_instruction = (
        f"Respond in the language with ISO code '{lang}'."
        if lang != "en"
        else "Respond in English."
    )

    # Build a richer system prompt so the LLM gives useful answers even for
    # edge cases like "0.0 mm precipitation" (= currently not raining).
    system_prompt = (
        "You are WeatherGPT, a friendly and knowledgeable AI weather assistant. "
        "Answer the user's weather question conversationally using the provided live data. "
        "Guidelines:\n"
        "- If precipitation is 0.0 mm, say it is NOT raining / no rain currently.\n"
        "- For 'will it rain' questions, check today's or tomorrow's forecast rain_sum — if 0 say unlikely, if >0 say how much.\n"
        "- Give a complete, helpful answer: mention condition, temperature, and any relevant details.\n"
        "- Use natural human language — avoid raw numbers without units or context.\n"
        "- Add a short practical tip if relevant (e.g. carry an umbrella, stay hydrated).\n"
        "- Keep the answer to 2-3 sentences max.\n"
        f"- {lang_instruction}"
    )

    user_prompt = (
        f"User asked: '{question}'\n"
        f"City: {city}\n"
        f"Intent: {intent}\n"
        f"Live weather data: {json.dumps(weather_data, ensure_ascii=False)}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    answer = _call_groq(messages, max_tokens=250)
    if answer:
        return answer.strip()
    return None