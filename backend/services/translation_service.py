from deep_translator import GoogleTranslator


def translate_text(text: str, target_lang: str = "en"):
    if target_lang == "en" or not text:
        return text
    try:
        return GoogleTranslator(source="auto", target=target_lang).translate(text)
    except Exception:
        return text  # if translation fails, just return the original text
