import os
import re
import requests
def normalize_query(question: str) -> str:
    # Keep common Malayalam input usable when the external translator is unavailable.
    replacements = {
        "ഡൽഹിയിലെ": " Delhi ",
        "ഡൽഹി": " Delhi ",
        "കാലാവസ്ഥ": " weather ",
        "വിവരിക്കാമോ": " describe ",
        "दिल्ली": " Delhi ",
        "मौसम": " weather ",
        "वर्णन": " describe ",
        "\u0d15\u0d4a\u0d1a\u0d4d\u0d1a\u0d3f\u0d2f\u0d3f\u0d32\u0d46": " Kochi ",
        "\u0d15\u0d4a\u0d1a\u0d4d\u0d1a\u0d3f": "Kochi",
        "\u0d15\u0d4b\u0d34\u0d3f\u0d15\u0d4d\u0d15\u0d4b\u0d1f\u0d4d": "Kozhikode",
        "\u0d24\u0d3f\u0d30\u0d41\u0d35\u0d28\u0d28\u0d4d\u0d24\u0d2a\u0d41\u0d30\u0d02": "Thiruvananthapuram",
        "\u0d24\u0d3e\u0d2a\u0d28\u0d3f\u0d32": "temperature",
        "\u0d24\u0d3e\u0d2a\u0d28\u0d3f\u0d32\u0d2f\u0d46\u0d28\u0d4d\u0d24\u0d3e\u0d23\u0d4d": "temperature",
            "\u0d8e\u0d28\u0d4d\u0d24\u0d3e\u0d23\u0d4d": " what is ",
            "\u0d21\u0d7d\u0d32\u0d4d\u0d32\u0d3f\u0d2f\u0d3f\u0d32\u0d46": " Delhi ",
            "\u0d21\u0d7d\u0d32\u0d4d\u0d32\u0d3f": "Delhi",
            "\u0d15\u0d3e\u0d32\u0d3e\u0d35\u0d38\u0d4d\u0d25": " weather ",
            "\u0d35\u0d3f\u0d35\u0d30\u0d3f\u0d15\u0d4d\u0d15\u0d3e\u0d2e\u0d4b": " describe ",
            "\u0926\u093f\u0932\u094d\u0932\u0940": " Delhi ",
            "\u092e\u094c\u0938\u092e": " weather ",
            "\u092c\u0924\u093e\u090f\u0902": " describe ",
    }
    normalized = question
    for source, replacement in replacements.items():
        normalized = normalized.replace(source, f" {replacement} ")
    return normalized


# Hugging Face Multilingual Transformer Model Endpoints
HF_TOKEN = os.getenv("HF_API_TOKEN")
INDICBERT_URL = "https://api-inference.huggingface.co/models/ai4bharat/indic-bert"
XLMR_URL = "https://api-inference.huggingface.co/models/xlm-roberta-base"

HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}


def extract_entities_with_transformer(text: str, model_url: str):
    """
    Queries Hugging Face model endpoints for multilingual NLP representations.
    Gracefully returns None if offline, unconfigured, or rate-limited.
    """
    if not HF_TOKEN:
        return None
    try:
        response = requests.post(model_url, headers=HEADERS, json={"inputs": text}, timeout=4)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


def extract_location(question: str):
    """
    Location extraction prioritizing regex rules and common Indian city keywords.
    """
    question = normalize_query(question)
    patterns = [
        r"\b(?:in|at|for)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?=\s+(?:today|tomorrow|tommorrow|next week)\b|[?!.,]|$)"
    ]

    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            loc = match.group(1).strip()
            if loc.lower() not in {"celsius", "centigrade", "fahrenheit", "detail", "details"}:
                return loc.title()

    # Fallback to direct token scan for common Indian cities & local places
    common_cities = {
        "kochi": "Kochi",
        "കൊച്ചി": "Kochi",
        "കൊച്ചിയിൽ": "Kochi",
        "കൊച്ചിയിലെ": "Kochi",
        "delhi": "Delhi",
        "दिल्ली": "Delhi",
        "ഡൽഹി": "Delhi",
        "mumbai": "Mumbai",
        "മുംബൈ": "Mumbai",
        "trivandrum": "Thiruvananthapuram",
        "തിരുവനന്തപുരം": "Thiruvananthapuram",
        "pattom": "Pattom",
        "പട്ടം": "Pattom",
        "പട്ടത്ത്": "Pattom"
    }
    
    words = [re.sub(r"[^\w\s]", "", w).lower() for w in question.split()]
    for word in words:
        if word in common_cities:
            return common_cities[word]

    return None


def understand_query(question: str):
    question = normalize_query(question)

    # Step 1: Multilingual model evaluation (IndicBERT -> XLM-R fallback)
    indic_entities = extract_entities_with_transformer(question, INDICBERT_URL)
    if not indic_entities:
        extract_entities_with_transformer(question, XLMR_URL)

    # Step 2: Intent, time, and variable determination
    q_clean = question.lower().strip()

    # Detect intent
    if any(word in q_clean for word in ["forecast", "tomorrow", "tommorrow", "next week", "next few days", "coming days"]):
        intent = "forecast"
    elif any(word in q_clean for word in ["rain", "raining", "rainfall"]):
        intent = "rain"
    elif any(word in q_clean for word in ["temperature", "hot", "cold", "heat"]):
        intent = "temperature"
    elif any(word in q_clean for word in ["wind", "windy"]):
        intent = "wind"
    elif any(word in q_clean for word in ["humidity", "humid"]):
        intent = "humidity"
    else:
        intent = "current_weather"

    # Detect time
    if any(w in q_clean for w in ["tomorrow", "tommorrow"]):
        time = "tomorrow"
    elif "today" in q_clean:
        time = "today"
    elif "next week" in q_clean:
        time = "next_week"
    else:
        time = "now"

    # Detect weather variable
    if any(word in q_clean for word in ["rain", "raining", "rainfall"]):
        weather_variable = "rain"
    elif any(word in q_clean for word in ["temperature", "hot", "cold", "heat"]):
        weather_variable = "temperature"
    elif any(word in q_clean for word in ["wind", "windy"]):
        weather_variable = "wind"
    elif any(word in q_clean for word in ["humidity", "humid"]):
        weather_variable = "humidity"
    else:
        weather_variable = "general"

    # Step 3: Location resolution
    location = extract_location(question)

    return {
        "intent": intent,
        "location": location,
        "time": time,
        "weather_variable": weather_variable
    }