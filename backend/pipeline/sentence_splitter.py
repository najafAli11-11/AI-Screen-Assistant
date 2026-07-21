import re


# Sentence terminators across supported languages:
# .  !  ?  ۔ (Urdu full stop)  ؟ (Arabic question mark)  । (Devanagari danda)
# NOTE: the Arabic comma (U+060C) is intentionally NOT a terminator — treating
# it as one chopped Urdu sentences mid-clause and produced choppy TTS.
_TERMINATORS = ".!?۔؟।"

_SENTENCE_BOUNDARY_PATTERN = re.compile(rf'(?<=[{_TERMINATORS}])\s+')

_SENTENCE_END = re.compile(rf'[{_TERMINATORS}]')


def split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    parts = _SENTENCE_BOUNDARY_PATTERN.split(text)
    result = [part.strip() for part in parts if part.strip()]
    return result or [text]


def is_sentence_complete(buffer: str) -> bool:
    if not buffer:
        return False
    return bool(_SENTENCE_END.search(buffer.rstrip()))
