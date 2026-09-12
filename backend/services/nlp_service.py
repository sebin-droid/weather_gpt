import re


def understand_query(question: str):

    question = question.lower().strip()

    # -----------------------------
    # Detect intent
    # -----------------------------

    if any(word in question for word in [
        "forecast",
        "tomorrow",
        "next week",
        "next few days",
        "coming days"
    ]):

        intent = "forecast"

    elif any(word in question for word in [
        "rain",
        "raining",
        "rainfall"
    ]):

        intent = "rain"

    elif any(word in question for word in [
        "temperature",
        "hot",
        "cold",
        "heat"
    ]):

        intent = "temperature"

    elif any(word in question for word in [
        "wind",
        "windy"
    ]):

        intent = "wind"

    elif any(word in question for word in [
        "humidity",
        "humid"
    ]):

        intent = "humidity"

    else:

        intent = "current_weather"

    # -----------------------------
    # Detect time
    # -----------------------------

    if "tomorrow" in question:

        time = "tomorrow"

    elif "today" in question:

        time = "today"

    elif "next week" in question:

        time = "next_week"

    else:

        time = "now"

    # -----------------------------
    # Detect weather variable
    # -----------------------------

    if any(word in question for word in [
        "rain",
        "raining",
        "rainfall"
    ]):

        weather_variable = "rain"

    elif any(word in question for word in [
        "temperature",
        "hot",
        "cold",
        "heat"
    ]):

        weather_variable = "temperature"

    elif any(word in question for word in [
        "wind",
        "windy"
    ]):

        weather_variable = "wind"

    elif any(word in question for word in [
        "humidity",
        "humid"
    ]):

        weather_variable = "humidity"

    else:

        weather_variable = "general"

    # -----------------------------
    # Detect location
    # -----------------------------

    location = extract_location(question)

    return {
        "intent": intent,
        "location": location,
        "time": time,
        "weather_variable": weather_variable
    }


def extract_location(question: str):

    patterns = [
        r"\b(?:in|at|for)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)*?)(?=\s+(?:today|tomorrow|next week)\b|[?!.,]|$)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            question
        )

        if match:

            location = match.group(1).strip()

            if location.lower() not in {"celsius", "centigrade", "fahrenheit"}:

                return location.title()

    return None