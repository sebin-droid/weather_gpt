"""
translate.py
------------
This file creates a "translate" endpoint (a URL the frontend can call)
using FastAPI (a Python tool for building web APIs).

When the frontend sends a request to /translate with some text and a
language code, this file:
  1. Receives the request
  2. Calls translate_text() from translation_service.py
  3. Sends back the translated text

Example request (what the frontend sends):
    POST /translate
    {
        "text": "It will rain tomorrow in Mumbai",
        "target_lang": "hi"
    }

Example response (what the frontend gets back):
    {
        "translated_text": "मुंबई में कल बारिश होगी",
        "target_lang": "hi",
        "source_lang": "auto"
    }
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Import our translation functions from translation_service.py
from services.translation_service import translate_text, get_supported_languages


# ---------- Create the Router ----------
# A "router" is like a mini-app that handles a specific group of URLs.
# All URLs in this file will start with /translate.
router = APIRouter(
    prefix="/translate",       # All URLs here start with /translate
    tags=["Translation"],      # Groups these endpoints together in docs
)


# ---------- Define what a request looks like ----------
# This tells FastAPI: "When someone sends a request, I expect these fields."
# Think of it like a form with required and optional fields.

class TranslateRequest(BaseModel):
    """What the frontend must send us."""
    text: str                          # The text to translate (required)
    target_lang: str                   # Language code like "hi" (required)
    source_lang: str = "auto"          # Source language (optional, defaults to auto-detect)


class TranslateResponse(BaseModel):
    """What we send back to the frontend."""
    translated_text: str               # The translated text
    target_lang: str                   # Which language we translated to
    source_lang: str                   # Which language the original was in


# ---------- Endpoint 1: Translate text ----------
@router.post("/", response_model=TranslateResponse)
def translate_endpoint(request: TranslateRequest):
    """
    Receives text and a target language, returns the translated text.

    How it works:
      1. The frontend sends: {"text": "Hello", "target_lang": "hi"}
      2. We call translate_text("Hello", "hi")
      3. We send back: {"translated_text": "नमस्ते", ...}
    """

    # Check that the text isn't empty
    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=400,
            detail="Text cannot be empty."
        )

    # Check that the language code is one we support
    supported = get_supported_languages()
    if request.target_lang not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Language '{request.target_lang}' is not supported. "
                   f"Supported: {list(supported.keys())}"
        )

    # Do the translation
    translated = translate_text(
        text=request.text,
        target_lang=request.target_lang,
        source_lang=request.source_lang,
    )

    # Send back the result
    return TranslateResponse(
        translated_text=translated,
        target_lang=request.target_lang,
        source_lang=request.source_lang,
    )


# ---------- Endpoint 2: List supported languages ----------
@router.get("/languages")
def list_languages():
    """
    Returns the list of languages we can translate to.

    The frontend can call GET /translate/languages to show a
    dropdown menu of available languages.

    Returns something like:
        {"languages": {"en": "English", "hi": "Hindi", ...}}
    """
    return {"languages": get_supported_languages()}
