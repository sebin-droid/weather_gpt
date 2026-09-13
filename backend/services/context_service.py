"""
context_service.py
------------------
Short-term conversation memory and context resolution for WeatherGPT chat.

Responsibilities:
  - detect_follow_up()              → Is this a follow-up message?
  - extract_location_from_history() → Pull last known city from chat history
  - extract_context_from_history()  → Pull last known intent/time/weather state
  - resolve_conversation_context()  → Main entry point; returns ConversationContext
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from services.nlp_service import understand_query


# ---------------------------------------------------------------------------
# Follow-up detection
# ---------------------------------------------------------------------------

_FOLLOWUP_PHRASES: set[str] = {
    # Elaboration
    "more", "tell more", "tell me more", "elaborate", "explain", "describe",
    "describe more", "give more", "more details", "more detail", "more info",
    "more information", "show more", "show details", "show me more",
    "brief me", "brief", "summary", "summarize", "details",
    "tell me about the situation", "more about the situation",
    "what does that mean", "what does this mean",
    "in detail", "in detailed manner", "detailed manner", "detailed",
    "explain simple", "explain simply", "explain simple way", "explain in simple way",
    "in a simple way", "in simple words", "simply", "simple way",
    # Reference words
    "why", "how", "how so", "what else", "anything else",
    "what about it", "it", "this", "that", "there", "here",
    "this city", "that place", "this place", "same city",
    # Comparisons
    "compare", "compare it", "compare with tomorrow",
    "compare it with tomorrow", "versus", "vs",
    # Single-word attribute follow-ups
    "humidity", "wind", "temperature", "rain", "fog", "snow",
    "pressure", "uv", "visibility", "precipitation",
    # Advice follow-ups
    "should i carry an umbrella", "should i take an umbrella",
    "can i go outside", "is it okay to go outside",
    "can i travel", "is it good for travel", "should i go out",
    "is it safe to go out", "can i play outside",
    # Informal
    "and?", "so?", "ok and?", "then?", "okay", "how bad is it",
    "how good is it", "is it bad", "is it good",
}

_FOLLOWUP_PATTERNS: list[str] = [
    r"^(what\s+about\s+(it|that|there|this|tomorrow|today|tonight|humidity|wind|temperature|rain|forecast|the\s+situation|the\s+next\s+day|the\s+day\s+after))\b",
    r"^(how\s+about\s+(it|that|there|this|tomorrow|humidity|wind|temperature|rain))\b",
    r"^(and\s+(humidity|wind|temperature|rain|tomorrow|forecast|what|the))\b",
    r"^(is\s+it\s+(hot|cold|windy|humid|rainy|cloudy|sunny|ok|fine|going\s+to|safe))\b",
    r"^(will\s+it\s+rain)\s*\??$",
    r"^(will\s+it\s+be\s+(rainy|cloudy|sunny|hot|cold|windy))\s*\??$",
    r"^(rain\s+tomorrow)\s*\??$",
    r"^(tomorrow)\s*\??$",
    r"^(tonight)\s*\??$",
    r"^(next\s+week)\s*\??$",
    r"^(what\s+about\s+tomorrow)\b",
    r"^(day\s+after)\b",
    r"^(the\s+day\s+after)\b",
    r"^(the\s+next\s+day)\b",
    r"^(should\s+i\s+(carry|take|bring|wear|go|travel|go out|play))\b",
    r"^(can\s+i\s+(go|travel|play|work))\b",
    r"^(give\s+me\s+(more|details|information))\b",
    r"^(tell\s+me\s+(more|about))\b",
    r"^(explain\s+(that|this|more|it))\b",
]


def _normalise(text: str) -> str:
    return text.lower().strip().rstrip("!?,.")


def detect_follow_up(question: str, history: list[dict]) -> bool:
    """
    Returns True if the current question is a follow-up to a previous message.
    A follow-up requires: matching phrase/pattern AND existing history.
    """
    if not history:
        return False

    t = _normalise(question)

    if t in _FOLLOWUP_PHRASES:
        return True

    for phrase in _FOLLOWUP_PHRASES:
        if t.startswith(phrase) and len(t) < len(phrase) + 30:
            return True

    for pattern in _FOLLOWUP_PATTERNS:
        if re.match(pattern, t):
            return True

    return False


# ---------------------------------------------------------------------------
# History extraction helpers
# ---------------------------------------------------------------------------

def extract_location_from_history(history: list[dict]) -> str | None:
    """Walk history (newest first) to find the last known city."""
    for turn in reversed(history):
        if turn.get("role") == "assistant":
            loc = turn.get("location")
            if loc:
                return loc
            # Parse from text: "In Kochi on..." or "Kochi is currently..."
            text = turn.get("content", "")
            m = re.search(r"\b(?:in|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b", text)
            if m:
                candidate = m.group(1)
                # Avoid false positives like "In Mumbai on 2026-09-14"
                if candidate not in {"Tomorrow", "Today", "Tonight"}:
                    return candidate
        elif turn.get("role") == "user":
            text = turn.get("content", "")
            q = understand_query(text)
            if q.get("location"):
                return q["location"]
    return None


def extract_context_from_history(history: list[dict]) -> dict:
    """
    Extract the last known intent, weather_variable, time, and weather_data
    from history. Returns sensible defaults if nothing found.
    """
    for turn in reversed(history):
        if turn.get("role") == "assistant":
            ctx = turn.get("context")
            if ctx and isinstance(ctx, dict):
                return ctx
    return {
        "intent": "current_weather",
        "weather_variable": "general",
        "time": "now",
        "weather_data": None,
    }


# ---------------------------------------------------------------------------
# ConversationContext dataclass
# ---------------------------------------------------------------------------

@dataclass
class ConversationContext:
    question: str
    lang: str
    is_follow_up: bool
    resolved_location: str | None
    intent: str
    weather_variable: str
    time: str
    history: list[dict] = field(default_factory=list)
    previous_weather_data: Any = None    # dict (current) or list (forecast)
    # For extensibility (future: vegetation, route, NDVI, etc.)
    domain: str = "weather"


# ---------------------------------------------------------------------------
# Main resolver
# ---------------------------------------------------------------------------

def resolve_conversation_context(
    question: str,
    lang: str,
    history: list[dict],
) -> ConversationContext:
    """
    Main entry point. Returns a fully resolved ConversationContext.

    Priority:
      1. Explicit info in current question
      2. Previous conversation context (location, intent, time)
      3. Ask user
    """
    is_followup = detect_follow_up(question, history)

    # NLP on current question
    query = understand_query(question)

    # --- Location: current question wins, then history ---
    resolved_location = query.get("location")
    if not resolved_location:
        resolved_location = extract_location_from_history(history)

    # --- Intent / variable / time from current question ---
    intent = query.get("intent", "current_weather")
    weather_variable = query.get("weather_variable", "general")
    time = query.get("time", "now")

    # --- Follow-up: fully inherit previous context when current is vague ---
    if is_followup and history:
        prev_ctx = extract_context_from_history(history)

        # If NLP didn't detect anything specific in the current question,
        # inherit everything from the previous turn (including "forecast" intent!)
        if intent == "current_weather" and weather_variable == "general":
            intent = prev_ctx.get("intent", "current_weather")
            weather_variable = prev_ctx.get("weather_variable", "general")

        # Inherit time only if current question didn't specify one
        if time == "now":
            prev_time = prev_ctx.get("time", "now")
            time = prev_time

    # --- Previous weather data (for LLM to reuse without re-fetching) ---
    previous_weather_data: Any = None
    for turn in reversed(history):
        if turn.get("role") == "assistant":
            wd = turn.get("weather_data")
            if wd is not None:
                previous_weather_data = wd
                break

    return ConversationContext(
        question=question,
        lang=lang,
        is_follow_up=is_followup,
        resolved_location=resolved_location,
        intent=intent,
        weather_variable=weather_variable,
        time=time,
        history=history[-10:],
        previous_weather_data=previous_weather_data,
        domain="weather",
    )
