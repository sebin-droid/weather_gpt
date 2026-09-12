import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def speech_to_text(audio_file_bytes: bytes, filename: str = "audio.wav") -> str:
    """Sends audio bytes directly to Groq's Whisper large-v3 endpoint."""
    if not os.getenv("GROQ_API_KEY"):
        return ""
    try:
        transcription = client.audio.transcriptions.create(
            file=(filename, audio_file_bytes),
            model="whisper-large-v3",
            response_format="text",
            temperature=0.0
        )
        return transcription.strip()
    except Exception as e:
        print(f"Whisper transcription error: {e}")
        return ""