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

import re


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

TRANSLATION_ERROR_MARKERS = (
    "error 500",
    "server error",
    "that's an error",
    "thatâs an error",
)


def fallback_translate(text: str, target_lang: str) -> str:
    patterns = {
        "ml": [
            (r"Please mention a city name\.", "ദയവായി ഒരു നഗരത്തിന്റെ പേര് നൽകുക."),
            (r"City not found", "നഗരം കണ്ടെത്താനായില്ല."),
            (r"The current temperature in (.+) is ([\d.]+) C\.", r"\1 ലെ നിലവിലെ താപനില \2 C ആണ്."),
            (r"In (.+), current precipitation is ([\d.]+) mm\.", r"\1 ലെ നിലവിലെ മഴയുടെ അളവ് \2 mm ആണ്."),
            (r"The current wind speed in (.+) is ([\d.]+) km/h\.", r"\1 ലെ കാറ്റിന്റെ വേഗത \2 km/h ആണ്."),
            (r"The current humidity in (.+) is ([\d.]+)%\.", r"\1 ലെ നിലവിലെ ഈർപ്പം \2% ആണ്."),
            (r"In (.+), the current condition is (.+), the temperature is ([\d.]+) C, humidity is ([\d.]+)%, precipitation is ([\d.]+) mm, and wind speed is ([\d.]+) km/h\.", r"\1 ലെ നിലവിലെ കാലാവസ്ഥ \2 ആണ്. താപനില \3 C, ഈർപ്പം \4%, മഴ \5 mm, കാറ്റിന്റെ വേഗത \6 km/h ആണ്."),
        ],
        "hi": [
            (r"Please mention a city name\.", "कृपया किसी शहर का नाम बताएं।"),
            (r"City not found", "शहर नहीं मिला।"),
            (r"The current temperature in (.+) is ([\d.]+) C\.", r"\1 में वर्तमान तापमान \2 C है।"),
            (r"In (.+), current precipitation is ([\d.]+) mm\.", r"\1 में वर्तमान वर्षा \2 mm है।"),
            (r"The current wind speed in (.+) is ([\d.]+) km/h\.", r"\1 में वर्तमान हवा की गति \2 km/h है।"),
            (r"The current humidity in (.+) is ([\d.]+)%\.", r"\1 में वर्तमान आर्द्रता \2% है।"),
            (r"In (.+), the current condition is (.+), the temperature is ([\d.]+) C, humidity is ([\d.]+)%, precipitation is ([\d.]+) mm, and wind speed is ([\d.]+) km/h\.", r"\1 में वर्तमान मौसम \2 है। तापमान \3 C, आर्द्रता \4%, वर्षा \5 mm और हवा की गति \6 km/h है।"),
        ],
    }
    for pattern, replacement in patterns.get(target_lang, []):
        if re.fullmatch(pattern, text):
            return re.sub(pattern, replacement, text)
    return text


def matches_language(text: str, target_lang: str) -> bool:
    if target_lang == "ml":
        return bool(re.search(r"[\u0d00-\u0d7f]", text))
    if target_lang == "hi":
        return bool(re.search(r"[\u0900-\u097f]", text))
    return True


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
        from deep_translator import GoogleTranslator

        # Create a translator object that knows:
        #   - what language the text is in (source)
        #   - what language we want (target)
        translator = GoogleTranslator(source=source_lang, target=target_lang)

        # Actually perform the translation and return the result.
        translated = translator.translate(text)
        if not translated or not matches_language(translated, target_lang) or any(
            marker in translated.lower() for marker in TRANSLATION_ERROR_MARKERS
        ):
            raise RuntimeError("Translation service returned an error response")
        return translated

    except Exception as e:
        # If anything goes wrong (no internet, unsupported language, etc.),
        # print the error for debugging but return the original text
        # so the app keeps working.
        print(f"[Translation Error] {e}")
        return fallback_translate(text, target_lang)
