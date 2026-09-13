"""
llm_service.py
--------------
LLM integration for WeatherGPT.

PRIMARY:  Qwen/Qwen3-8B via Hugging Face InferenceClient
FALLBACK: Groq (llama-3.1-8b-instant) if HF is unavailable

Functions:
  _call_qwen()           — Qwen3-8B via HF InferenceClient
  _call_groq()           — Groq fallback
  _call_llm()            — tries Qwen first, falls back to Groq
  extract_query_info()   — parse intent/location/time/variable from question
  build_llm_messages()   — construct message list with conversation history
  make_friendly_answer() — generate a conversational weather answer
"""

from __future__ import annotations

import os
import json
import re
import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

HF_TOKEN    = os.getenv("HF_TOKEN")
HF_MODEL    = os.getenv("HF_MODEL", "Qwen/Qwen3-8B")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL    = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL  = "llama-3.1-8b-instant"


# ---------------------------------------------------------------------------
# Qwen3-8B via HuggingFace InferenceClient (primary)
# ---------------------------------------------------------------------------

def _call_qwen(
    messages: list[dict],
    max_tokens: int = 512,
    temperature: float = 0.3,
) -> str | None:
    """
    Call Qwen/Qwen3-8B via the Hugging Face Inference API.
    Returns the assistant message text, or None on any error.

    Qwen3 supports a thinking mode (enabled by default). We disable it
    by passing enable_thinking=False so responses are fast and direct.
    """
    if not HF_TOKEN:
        return None
    try:
        from huggingface_hub import InferenceClient
        client = InferenceClient(
            provider="auto",
            api_key=HF_TOKEN,
        )

        # Build clean messages list (no extra metadata fields)
        clean_msgs = [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m.get("role") in ("system", "user", "assistant") and m.get("content")
        ]

        response = client.chat.completions.create(
            model=HF_MODEL,
            messages=clean_msgs,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        text = response.choices[0].message.content or ""
        # Strip any <think>...</think> blocks Qwen3 may still emit
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        return text if text else None
    except Exception as e:
        print(f"[Qwen Error] {e}")
        return None


# ---------------------------------------------------------------------------
# Groq (fallback)
# ---------------------------------------------------------------------------

def _call_groq(
    messages: list[dict],
    max_tokens: int = 300,
    json_mode: bool = False,
) -> str | None:
    """Call Groq API (llama-3.1-8b-instant). Returns assistant text or None."""
    if not GROQ_API_KEY:
        return None
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        data: dict = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": m["role"], "content": m["content"]}
                for m in messages
                if m.get("role") in ("system", "user", "assistant") and m.get("content")
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
        if json_mode:
            data["response_format"] = {"type": "json_object"}
        response = requests.post(GROQ_URL, headers=headers, json=data, timeout=12)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[Groq Error] {e}")
        return None


# ---------------------------------------------------------------------------
# Unified LLM caller: Qwen → Groq fallback
# ---------------------------------------------------------------------------

def _call_llm(
    messages: list[dict],
    max_tokens: int = 300,
    temperature: float = 0.3,
    json_mode: bool = False,
) -> str | None:
    """Try Qwen first, fall back to Groq. Returns text or None."""
    if json_mode:
        # JSON mode is more reliable with Groq for structured extraction
        result = _call_groq(messages, max_tokens=max_tokens, json_mode=True)
        if result:
            return result
        # Try Qwen with explicit JSON instruction
        return _call_qwen(messages, max_tokens=max_tokens, temperature=temperature)

    result = _call_qwen(messages, max_tokens=max_tokens, temperature=temperature)
    if result:
        return result
    return _call_groq(messages, max_tokens=max_tokens)


# ---------------------------------------------------------------------------
# Structured query extraction (used by nlp_service)
# ---------------------------------------------------------------------------

def extract_query_info(question: str) -> dict | None:
    """
    Ask the LLM to extract structured query info from a weather question.
    Returns { intent, location, time, weather_variable } or None.
    """
    system_prompt = (
        "You are a weather query parser. Extract structured information from a user's weather question.\n"
        "Return ONLY a valid JSON object with exactly these keys:\n"
        "  - intent: one of [forecast, rain, temperature, wind, humidity, current_weather]\n"
        "  - location: the city/place name as a properly capitalised string, or null if not mentioned\n"
        "  - time: one of [now, today, tonight, tomorrow, weekend, next_week]\n"
        "  - weather_variable: one of [rain, temperature, wind, humidity, general]\n\n"
        "Rules:\n"
        "- 'will it rain', 'going to rain', 'chance of rain' → intent=forecast, weather_variable=rain\n"
        "- 'is it raining now' → intent=rain, weather_variable=rain, time=now\n"
        "- tomorrow/forecast/next few days/weekend → intent=forecast\n"
        "- rain/drizzle/pour/storm/flood/shower → weather_variable=rain\n"
        "- temperature/hot/cold/feels like/chilly/warm → intent=temperature, weather_variable=temperature\n"
        "- wind/windy/breeze/gust → intent=wind, weather_variable=wind\n"
        "- humidity/muggy/damp/moisture → intent=humidity, weather_variable=humidity\n"
        "- 'will it rain in <city>' with no time → time=today\n"
        "- The question may be in Hindi, Tamil, Telugu, Bengali, Malayalam — extract accordingly.\n"
        "Return ONLY the JSON object, no explanation, no markdown."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]
    raw = _call_llm(messages, max_tokens=120, temperature=0.1, json_mode=True)
    if not raw:
        return None
    # Safe JSON parsing — strip markdown fences if present
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        parsed = json.loads(raw)
        required = {"intent", "location", "time", "weather_variable"}
        if required.issubset(parsed.keys()):
            return parsed
    except (json.JSONDecodeError, KeyError, ValueError):
        pass
    return None


# ---------------------------------------------------------------------------
# LLM message construction
# ---------------------------------------------------------------------------

def build_llm_messages(
    question: str,
    city: str,
    weather_data: Any,
    intent: str,
    time: str,
    lang: str,
    history: list[dict],
    is_follow_up: bool = False,
) -> list[dict]:
    """
    Build the messages array for the LLM chat completion call.

    System prompt + last N conversation turns + current user question
    with weather data injected.
    """
    from typing import Any  # local import to avoid circular

    lang_instruction = (
        f"Respond in the language with ISO code '{lang}'."
        if lang != "en"
        else "Respond in English."
    )

    # Describe what data we are providing
    if isinstance(weather_data, list):
        data_label = f"7-day forecast data (list of daily records) for {city}"
        # Trim to first 4 days to keep prompt manageable
        data_str = json.dumps(weather_data[:4], ensure_ascii=False)
    else:
        data_label = f"current weather data for {city}"
        data_str = json.dumps(weather_data, ensure_ascii=False)

    system_prompt = f"""You are WeatherGPT, a friendly, accurate AI weather assistant.

CORE RULES:
1. Respond naturally and conversationally in a descriptive, human-like manner. Provide rich, wordy explanations instead of just reading out numbers.
2. Use ONLY the weather data provided below. NEVER invent or guess values.
3. If precipitation is 0.0 mm → explain clearly that no rain is expected.
4. For follow-up questions, continue the previous topic — do NOT switch to current weather unless the user asks.
5. If the user asks for a simple explanation, explain it like they are a 10-year-old using simple words.
6. If the user asks for details or a "detailed manner", provide a comprehensive, multi-sentence breakdown of the conditions, how it feels, and what it means for their day.
7. Do NOT mention "intent", "context", "API", "model", or any technical internals.
8. Do NOT say "according to the context" or "based on your previous question".
9. For "why?" questions: explain only what the data supports; if cause data is unavailable, say so honestly.
10. For advice questions (umbrella, travel, outdoor activity): use actual weather values to give a helpful recommendation.
11. Add a short practical tip when relevant.
12. {lang_instruction}

Current city: {city}
Current topic: {intent} ({time})
Weather data provided ({data_label}):
{data_str}"""

    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    # Inject last N conversation turns (content only)
    for turn in history[-8:]:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    # Current question
    messages.append({"role": "user", "content": question})

    return messages


# ---------------------------------------------------------------------------
# Public answer-generation function
# ---------------------------------------------------------------------------

def make_friendly_answer(
    weather_data,
    city: str,
    question: str,
    lang: str = "en",
    intent: str = "current_weather",
    time: str = "now",
    history: list[dict] | None = None,
    is_follow_up: bool = False,
) -> str | None:
    """
    Generate a natural, conversational weather answer.

    Tries Qwen/Qwen3-8B first, falls back to Groq.
    Returns None if both LLMs are unavailable.
    """
    if history is None:
        history = []

    messages = build_llm_messages(
        question=question,
        city=city,
        weather_data=weather_data,
        intent=intent,
        time=time,
        lang=lang,
        history=history,
        is_follow_up=is_follow_up,
    )

    answer = _call_llm(messages, max_tokens=350, temperature=0.35)
    if answer:
        return answer.strip()
    return None


# ---------------------------------------------------------------------------
# Type hint fix
# ---------------------------------------------------------------------------
from typing import Any