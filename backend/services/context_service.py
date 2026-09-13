"""
context_service.py
------------------
Short-term conversation memory and context resolution for WeatherGPT chat.

Responsibilities:
  - detect_follow_up()           → Is the current message a follow-up?
  - extract_location_from_history() → Pull last known city from chat history
  - extract_context_from_history()  → Pull last known intent/weather state
  - resolve_location()           → Current question location OR history location
  - resolve_intent()             → Current intent OR inherited from history
  - resolve_conversation_context()  → Main entry point; returns a full ConversationContext
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from services.nlp_service import understand_query


# ---------------------------------------------------------------------------
# Follow-up detection
# ---------------------------------------------------------------------------

# Phrases that signal the user is continuing a previous topic, not starting new
_FOLLOWUP_PHRASES: set[str] = {
    # Elaboration
    "more", "tell more", "tell me more", "elaborate", "explain", "describe",
    "describe more", "give more", "more details", "more detail", "more info",
    "more information", "show more", "show details", "show me more",
    "brief me", "brief", "summary", "summarize", "details",
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
    # Informal
    "and?", "so?", "ok and?", "then?", "okay",
}

# Regex patterns for follow-up detection (applied to normalised lowercase text)
_FOLLOWUP_PATTERNS: list[str] = [
    r"^(what\s+about\s+(it|that|there|this|tomorrow|today|tonight|humidity|wind|temperature|rain|forecast))\b",
    r"^(how\s+about\s+(it|that|there|this|tomorrow|humidity|wind|temperature|rain))\b",
    r"^(and\s+(humidity|wind|temperature|rain|tomorrow|forecast|what))\b",
    r"^(is\s+it\s+(hot|cold|windy|humid|rainy|cloudy|sunny|ok|fine))\b",
    r"^(will\s+it\s+rain)\s*\??$",           # "will it rain?" with NO city
    r"^(rain\s+tomorrow)\s*\??$",
    r"^(tomorrow)\s*\??$",
    r"^(tonight)\s*\??$",
    r"^(next\s+week)\s*\??$",
    r"^(what\s+about\s+tomorrow)\b",
    r"^(day\s+after)\b",
    r"^(the\s+day\s+after)\b",
]

# Words/patterns that strongly indicate a NEW location is mentioned
_NEW_LOCATION_PATTERN = re.compile(
    r"\b(in|at|for|near|around|of)\s+([A-Za-z\u0900-\u097F\u0D00-\u0D7F]+(?:\s+[A-Za-z]+)?)\b",
    re.IGNORECASE,
)


def _normalise(text: str) -> str:
    return text.lower().strip().rstrip("!?,.")


def detect_follow_up(question: str, history: list[dict]) -> bool:
    """
    Returns True if the current question appears to be a follow-up to a
    previous message rather than a brand-new, self-contained query.

    A question is treated as a follow-up when:
    1. It matches a known follow-up phrase / pattern, AND
    2. There is some existing conversation history to follow up on.
    """
    if not history:
        return False  # No history → cannot be a follow-up

    t = _normalise(question)

    # Exact match in known follow-up set
    if t in _FOLLOWUP_PHRASES:
        return True

    # Starts with a known follow-up phrase
    for phrase in _FOLLOWUP_PHRASES:
        if t.startswith(phrase) and len(t) < len(phrase) + 25:
            return True

    # Regex patterns
    for pattern in _FOLLOWUP_PATTERNS:
        if re.match(pattern, t):
            return True

    return False


# ---------------------------------------------------------------------------
# History extraction helpers
# ---------------------------------------------------------------------------

def extract_location_from_history(history: list[dict]) -> str | None:
    """
    Walk the history (newest first) and extract the last city name that
    was mentioned either in the user's message or the assistant's reply.

    We look for the 'location' stored in assistant metadata if present,
    otherwise try to parse it from the assistant's text.
    """
    # Walk newest → oldest
    for turn in reversed(history):
        # If the frontend stores structured metadata alongside messages
        if turn.get("role") == "assistant":
            loc = turn.get("location")       # may be set by frontend
            if loc:
                return loc
            # Try to parse "in <City>" from assistant response
            text = turn.get("content", "")
            m = re.search(r"\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b", text)
            if m:
                return m.group(1)
        elif turn.get("role") == "user":
            # Parse from user message as fallback
            text = turn.get("content", "")
            # run a quick NLP pass
            q = understand_query(text)
            if q.get("location"):
                return q["location"]
    return None


def extract_context_from_history(history: list[dict]) -> dict:
    """
    Extract the last known intent, weather_variable, and time from history.
    Returns a dict with defaults if nothing found.
    """
    for turn in reversed(history):
        if turn.get("role") == "assistant":
            ctx = turn.get("context", {})
            if ctx:
                return ctx
    return {"intent": "current_weather", "weather_variable": "general", "time": "now"}


# ---------------------------------------------------------------------------
# ConversationContext dataclass
# ---------------------------------------------------------------------------

@dataclass
class ConversationContext:
    question: str
    lang: str
    is_follow_up: bool
    resolved_location: str | None    # city name ready for get_location()
    intent: str
    weather_variable: str
    time: str
    history: list[dict] = field(default_factory=list)
    previous_weather_data: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Main resolver
# ---------------------------------------------------------------------------

def resolve_conversation_context(
    question: str,
    lang: str,
    history: list[dict],
) -> ConversationContext:
    """
    Main entry point.  Given the raw question, language, and conversation
    history, return a fully resolved ConversationContext ready for the
    chat router to use.

    Flow:
      1. Detect whether this is a follow-up.
      2. Run NLP on the current question to get intent/location.
      3. If no location found → try to inherit from history.
      4. If intent is generic (follow-up) → inherit from history context.
      5. Return ConversationContext.
    """
    is_followup = detect_follow_up(question, history)

    # Run NLP (LLM-first, regex fallback) on the current question
    query = understand_query(question)

    # --- Location resolution ---
    resolved_location = query.get("location")

    if not resolved_location:
        # No location in current message → try history
        resolved_location = extract_location_from_history(history)

    # --- Intent / variable resolution ---
    intent = query.get("intent", "current_weather")
    weather_variable = query.get("weather_variable", "general")
    time = query.get("time", "now")

    # If we detected a follow-up and the NLP gives current_weather/general
    # for what looks like a refinement → inherit previous intent context
    if is_followup:
        prev_ctx = extract_context_from_history(history)
        # Only inherit if current query didn't detect something specific
        if intent == "current_weather" and weather_variable == "general":
            intent = "current_weather"         # keep as current unless overridden
            weather_variable = prev_ctx.get("weather_variable", "general")
        # Keep time if newly specified, else inherit
        if time == "now":
            time = prev_ctx.get("time", "now")

    # --- Extract previous weather data from history (for LLM context) ---
    previous_weather_data: dict[str, Any] = {}
    for turn in reversed(history):
        if turn.get("role") == "assistant" and turn.get("weather_data"):
            previous_weather_data = turn["weather_data"]
            break

    return ConversationContext(
        question=question,
        lang=lang,
        is_follow_up=is_followup,
        resolved_location=resolved_location,
        intent=intent,
        weather_variable=weather_variable,
        time=time,
        history=history[-10:],           # keep last 10 messages max
        previous_weather_data=previous_weather_data,
    )
