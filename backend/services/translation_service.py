"""
translation_service.py
----------------------
This file handles translating text from one language to another.
It uses the 'deep-translator' library which connects to Google Translate
for free — no API key or payment needed.

Usage example:
    from backend.services.translation_service import translate_text
    result = translate_text("Hello, how are you?", "hi")
    # result → "नमस्ते, आप कैसे हैं?"
"""

from deep_translator import GoogleTranslator


# ---------- Supported Languages ----------
# This dictionary maps a short code to the full language name.
# The short codes (like "hi", "ta") are standard language codes
# used by Google Translate.

SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "bn": "Bengali",
    "mr": "Marathi",
    "gu": "Gujarati",
    "kn": "Kannada",
    "ml": "Malayalam",
    "pa": "Punjabi",
    "ur": "Urdu",
    "or": "Odia",
    "as": "Assamese",
}


def get_supported_languages() -> dict:
    """
    Returns the dictionary of supported language codes and their names.

    Returns:
        dict: e.g. {"en": "English", "hi": "Hindi", ...}
    """
    return SUPPORTED_LANGUAGES


def translate_text(text: str, target_lang: str, source_lang: str = "auto") -> str:
    """
    Translates the given text into the target language.

    What the arguments mean:
        text        : The sentence/paragraph you want to translate.
        target_lang : The language code to translate INTO (e.g. "hi" for Hindi).
        source_lang : The language the text is currently in.
                      Default is "auto" which means Google will detect it
                      automatically.

    Returns:
        str: The translated text. If something goes wrong, it returns the
             original text unchanged so the app doesn't crash.
    """

    # If the target language is English, or no target is given,
    # just return the original text — no need to translate.
    if not target_lang or target_lang == "en":
        return text

    # If the text is empty or blank, nothing to translate.
    if not text or not text.strip():
        return text

    try:
        # Create a translator object that knows:
        #   - what language the text is in (source)
        #   - what language we want (target)
        translator = GoogleTranslator(source=source_lang, target=target_lang)

        # Actually perform the translation and return the result.
        translated = translator.translate(text)
        return translated

    except Exception as e:
        # If anything goes wrong (no internet, unsupported language, etc.),
        # print the error for debugging but return the original text
        # so the app keeps working.
        print(f"[Translation Error] {e}")
        return text
