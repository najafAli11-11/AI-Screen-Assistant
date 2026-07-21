"""Lightweight translation fallback.

Claude is already instructed to answer in the target language, so translation
is only a safety net. Whether a sentence needs translating is decided locally
from Unicode script ranges (no network round-trips); only the actual
translation goes through the network, and failures fall back to the original
sentence so captions are never lost.
"""

_LANGUAGE_MAP = {
    "ur": "urdu",
    "en": "english",
    "hi": "hindi",
    "urdu": "urdu",
    "english": "english",
    "hindi": "hindi",
}


def _script_of(text: str) -> str:
    """Best-effort script detection: arabic (Urdu), devanagari (Hindi), latin."""
    arabic = devanagari = latin = 0
    for ch in text:
        code = ord(ch)
        if 0x0600 <= code <= 0x06FF or 0x0750 <= code <= 0x077F or 0xFB50 <= code <= 0xFEFF:
            arabic += 1
        elif 0x0900 <= code <= 0x097F:
            devanagari += 1
        elif ("a" <= ch <= "z") or ("A" <= ch <= "Z"):
            latin += 1
    top = max(arabic, devanagari, latin)
    if top == 0:
        return "unknown"
    if top == arabic:
        return "arabic"
    if top == devanagari:
        return "devanagari"
    return "latin"


_EXPECTED_SCRIPT = {"ur": "arabic", "hi": "devanagari", "en": "latin"}


def needs_translation(text: str, target_lang: str) -> bool:
    expected = _EXPECTED_SCRIPT.get(target_lang.lower())
    if expected is None or not text.strip():
        return False
    detected = _script_of(text)
    if detected == "unknown":
        return False
    return detected != expected


def translate(text: str, target_lang: str) -> str:
    target = _LANGUAGE_MAP.get(target_lang.lower())
    if target is None:
        return text
    try:
        from deep_translator import GoogleTranslator

        translated = GoogleTranslator(source="auto", target=target).translate(text)
        return translated or text
    except Exception:
        return text
