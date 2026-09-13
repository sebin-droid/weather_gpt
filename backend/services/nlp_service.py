"""
nlp_service.py
--------------
Two-tier query understanding pipeline:

  Tier 1 (Primary)  — Ask the Groq LLM to extract intent / location / time /
                       weather_variable as structured JSON.  Works for any language
                       or phrasing without hand-crafted rules.

  Tier 2 (Fallback) — If the LLM is unavailable (no API key, timeout, quota) fall
                       back to an improved regex + keyword system that covers ~60
                       major Indian cities and a broader intent vocabulary.
"""

import re
from services.llm_service import extract_query_info


# ---------------------------------------------------------------------------
# Fallback Tier 2 — Regex / keyword pipeline
# ---------------------------------------------------------------------------

# ~60 major Indian cities + common script variants / suffixes
COMMON_CITIES: dict[str, str] = {
    # Kerala
    "kochi": "Kochi",
    "cochin": "Kochi",
    "kozhikode": "Kozhikode",
    "calicut": "Kozhikode",
    "thiruvananthapuram": "Thiruvananthapuram",
    "trivandrum": "Thiruvananthapuram",
    "thrissur": "Thrissur",
    "palakkad": "Palakkad",
    "kollam": "Kollam",
    "kannur": "Kannur",
    "malappuram": "Malappuram",
    "alappuzha": "Alappuzha",
    "alleppey": "Alappuzha",
    "pattom": "Pattom",

    # Tamil Nadu
    "chennai": "Chennai",
    "madras": "Chennai",
    "coimbatore": "Coimbatore",
    "madurai": "Madurai",
    "tiruchirappalli": "Tiruchirappalli",
    "trichy": "Tiruchirappalli",
    "salem": "Salem",
    "tirunelveli": "Tirunelveli",
    "vellore": "Vellore",
    "erode": "Erode",

    # Karnataka
    "bangalore": "Bangalore",
    "bengaluru": "Bangalore",
    "mysore": "Mysore",
    "mysuru": "Mysore",
    "hubli": "Hubli",
    "mangalore": "Mangalore",
    "mangaluru": "Mangalore",
    "belgaum": "Belgaum",
    "gulbarga": "Gulbarga",

    # Maharashtra
    "mumbai": "Mumbai",
    "bombay": "Mumbai",
    "pune": "Pune",
    "nagpur": "Nagpur",
    "nashik": "Nashik",
    "aurangabad": "Aurangabad",
    "solapur": "Solapur",

    # Delhi / NCR
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "noida": "Noida",
    "gurgaon": "Gurgaon",
    "gurugram": "Gurgaon",
    "faridabad": "Faridabad",

    # North India
    "agra": "Agra",
    "lucknow": "Lucknow",
    "kanpur": "Kanpur",
    "varanasi": "Varanasi",
    "benaras": "Varanasi",
    "allahabad": "Prayagraj",
    "prayagraj": "Prayagraj",
    "jaipur": "Jaipur",
    "jodhpur": "Jodhpur",
    "udaipur": "Udaipur",
    "amritsar": "Amritsar",
    "chandigarh": "Chandigarh",
    "shimla": "Shimla",
    "dehradun": "Dehradun",

    # East India
    "kolkata": "Kolkata",
    "calcutta": "Kolkata",
    "bhubaneswar": "Bhubaneswar",
    "patna": "Patna",
    "ranchi": "Ranchi",
    "guwahati": "Guwahati",

    # Telangana / AP
    "hyderabad": "Hyderabad",
    "secunderabad": "Hyderabad",
    "visakhapatnam": "Visakhapatnam",
    "vizag": "Visakhapatnam",
    "vijayawada": "Vijayawada",
    "warangal": "Warangal",

    # Goa
    "panaji": "Panaji",
    "goa": "Panaji",

    # Gujarat
    "ahmedabad": "Ahmedabad",
    "surat": "Surat",
    "vadodara": "Vadodara",
    "baroda": "Vadodara",
    "rajkot": "Rajkot",

    # Script variants (Malayalam)
    "കൊച്ചി": "Kochi",
    "കൊച്ചിയിൽ": "Kochi",
    "കൊച്ചിയിലെ": "Kochi",
    "കോഴിക്കോട്": "Kozhikode",
    "തിരുവനന്തപുരം": "Thiruvananthapuram",
    "ഡൽഹി": "Delhi",
    "ഡൽഹിയിലെ": "Delhi",
    "മുംബൈ": "Mumbai",
    "ബാംഗ്ലൂർ": "Bangalore",
    "ചെന്നൈ": "Chennai",
    # Script variants (Hindi / Devanagari)
    "दिल्ली": "Delhi",
    "मुंबई": "Mumbai",
    "बेंगलुरु": "Bangalore",
    "कोलकाता": "Kolkata",
    "चेन्नई": "Chennai",
    "हैदराबाद": "Hyderabad",
    "पुणे": "Pune",
    "जयपुर": "Jaipur",
    "लखनऊ": "Lucknow",
    "अहमदाबाद": "Ahmedabad",
}

# Multilingual normalisation map — translate common weather words in Indian
# scripts to English equivalents so the keyword matcher below works.
_NORMALIZE_MAP: dict[str, str] = {
    # Malayalam weather words
    "കാലാവസ്ഥ": " weather ",
    "മഴ": " rain ",
    "താപനില": " temperature ",
    "കാറ്റ്": " wind ",
    "ഈർപ്പം": " humidity ",
    "ഇന്ന്": " today ",
    "നാളെ": " tomorrow ",
    "വിവരിക്കാമോ": " describe ",
    "എന്താണ്": " what is ",
    # Hindi weather words
    "मौसम": " weather ",
    "बारिश": " rain ",
    "वर्षा": " rain ",
    "तापमान": " temperature ",
    "हवा": " wind ",
    "आर्द्रता": " humidity ",
    "आज": " today ",
    "कल": " tomorrow ",
    "वर्णन": " describe ",
    "बताएं": " describe ",
    # Tamil
    "வானிலை": " weather ",
    "மழை": " rain ",
    "வெப்பநிலை": " temperature ",
    "காற்று": " wind ",
    "இன்று": " today ",
    "நாளை": " tomorrow ",
    # Telugu
    "వాతావరణం": " weather ",
    "వర్షం": " rain ",
    "ఉష్ణోగ్రత": " temperature ",
    "గాలి": " wind ",
    "ఈరోజు": " today ",
    "రేపు": " tomorrow ",
    # Bengali
    "আবহাওয়া": " weather ",
    "বৃষ্টি": " rain ",
    "তাপমাত্রা": " temperature ",
    "বাতাস": " wind ",
    "আজ": " today ",
    "আগামীকাল": " tomorrow ",
}

# Intent keyword groups (English, after normalisation)
_FORECAST_WORDS = {
    "forecast", "tomorrow", "tommorrow", "next week", "next few days",
    "coming days", "this week", "weekend", "week", "days ahead",
    "will it", "going to", "will there", "chance of", "expected to",
    "likely to", "predict", "prediction",
}
_RAIN_WORDS = {
    "rain", "raining", "rainfall", "pour", "pouring", "drizzle",
    "drizzling", "shower", "storm", "flood", "precipitation", "rainy",
}
_TEMP_WORDS = {
    "temperature", "temp", "hot", "cold", "heat", "cool", "warm",
    "feels like", "chilly", "freezing", "boiling", "degree", "celsius",
}
_WIND_WORDS = {"wind", "windy", "gust", "breeze", "gale", "breezy"}
_HUMIDITY_WORDS = {"humidity", "humid", "muggy", "damp", "moisture", "sticky"}

# Future-tense phrases — upgrade rain/temp/wind intent to forecast
_FUTURE_PATTERNS = [
    r"\bwill\s+it\b",
    r"\bgoing\s+to\b",
    r"\bwill\s+there\s+be\b",
    r"\bchance\s+of\b",
    r"\bexpect(ed)?\b",
]

_TIME_MAP = {
    "tomorrow": "tomorrow",
    "tommorrow": "tomorrow",
    "tonight": "tonight",
    "today": "today",
    "next week": "next_week",
    "weekend": "weekend",
    "this week": "next_week",
}


def _normalize(text: str) -> str:
    """Replace non-Latin weather/time/place terms with English equivalents."""
    for src, repl in _NORMALIZE_MAP.items():
        text = text.replace(src, repl)
    return text


def _extract_location_fallback(question: str) -> str | None:
    """
    Try to extract a city name from *question* using:
    1. Direct match against the COMMON_CITIES dictionary (handles scripts too).
    2. Regex patterns that look for city names near prepositions or
       the word 'weather'.
    """
    q_lower = question.lower()

    # 1. Direct dictionary scan — strip punctuation for each token.
    tokens = [re.sub(r"[^\w\s]", "", w) for w in question.split()]
    for tok in tokens:
        if tok.lower() in COMMON_CITIES:
            return COMMON_CITIES[tok.lower()]
        if tok in COMMON_CITIES:  # script variants (exact case)
            return COMMON_CITIES[tok]

    # 2. Multi-word city check (e.g. "new delhi")
    for city_key, city_val in COMMON_CITIES.items():
        if " " in city_key and city_key in q_lower:
            return city_val

    # 3. Regex: "weather in <City>", "weather at <City>", "weather for <City>"
    patterns = [
        r"\b(?:in|at|for)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\b",
        r"\b([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+weather\b",
        r"\bweather\s+(?:of\s+|in\s+)?([A-Za-z]+(?:\s+[A-Za-z]+)?)\b",
    ]
    stop_words = {
        "celsius", "centigrade", "fahrenheit", "detail", "details",
        "the", "a", "an", "is", "are", "will", "be", "it", "like",
        "today", "tomorrow", "next", "week", "forecast",
    }
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            loc = match.group(1).strip()
            if loc.lower() not in stop_words:
                # Check if it maps to a known city; otherwise return as-is
                return COMMON_CITIES.get(loc.lower(), loc.title())

    return None


def _understand_query_fallback(question: str) -> dict:
    """Keyword/regex-based fallback for when the LLM is unavailable."""
    normalised = _normalize(question).lower().strip()

    # Detect if the question uses future-tense phrasing
    is_future = any(re.search(p, normalised) for p in _FUTURE_PATTERNS)

    # --- Intent detection ---
    if any(w in normalised for w in _FORECAST_WORDS):
        intent = "forecast"
    elif any(w in normalised for w in _RAIN_WORDS):
        # "will it rain" → forecast; "is it raining" → rain (current)
        intent = "forecast" if is_future else "rain"
    elif any(w in normalised for w in _TEMP_WORDS):
        intent = "forecast" if is_future else "temperature"
    elif any(w in normalised for w in _WIND_WORDS):
        intent = "wind"
    elif any(w in normalised for w in _HUMIDITY_WORDS):
        intent = "humidity"
    else:
        intent = "current_weather"

    # --- Time detection ---
    time = "now"
    for phrase, label in _TIME_MAP.items():
        if phrase in normalised:
            time = label
            break

    # --- Weather variable ---
    if any(w in normalised for w in _RAIN_WORDS):
        weather_variable = "rain"
    elif any(w in normalised for w in _TEMP_WORDS):
        weather_variable = "temperature"
    elif any(w in normalised for w in _WIND_WORDS):
        weather_variable = "wind"
    elif any(w in normalised for w in _HUMIDITY_WORDS):
        weather_variable = "humidity"
    else:
        weather_variable = "general"

    # --- Location ---
    location = _extract_location_fallback(_normalize(question))

    return {
        "intent": intent,
        "location": location,
        "time": time,
        "weather_variable": weather_variable,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def understand_query(question: str) -> dict:
    """
    Understand a user's weather question and return structured query info.

    Tries the LLM first (Tier 1).  Falls back to keyword matching (Tier 2)
    if the LLM is unavailable or returns bad output.

    Returns:
        {
            "intent": str,
            "location": str | None,
            "time": str,
            "weather_variable": str,
            "source": "llm" | "fallback"   ← for debugging
        }
    """
    # Tier 1 — LLM
    llm_result = extract_query_info(question)
    if llm_result:
        llm_result["source"] = "llm"
        # Sanitise location from LLM — map to canonical name if possible
        loc = llm_result.get("location")
        if loc:
            llm_result["location"] = COMMON_CITIES.get(loc.lower(), loc)
        return llm_result

    # Tier 2 — Regex / keyword fallback
    result = _understand_query_fallback(question)
    result["source"] = "fallback"
    return result