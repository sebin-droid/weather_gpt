import os
import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def ask_llm(prompt: str):
    if not GROQ_API_KEY:
        return None
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "allam-2-7b",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 150
        }
        response = requests.post(GROQ_URL, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


def make_friendly_answer(weather_data: dict, city: str, question: str):
    prompt = (
        f"The user asked: '{question}'. Here is the weather data for {city}: "
        f"{weather_data}. Reply in one short, friendly sentence answering their question."
    )
    answer = ask_llm(prompt)
    if answer:
        return answer.strip()
    return f"In {city}, the current condition is {weather_data.get('condition', 'unknown')}."