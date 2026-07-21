import asyncio
import base64
import io
import logging

from config import settings

logger = logging.getLogger(__name__)

_elevenlabs_client = None


def _gtts_synthesize_blocking(text: str, lang: str) -> bytes:
    from gtts import gTTS

    buffer = io.BytesIO()
    gTTS(text=text, lang=lang, slow=False).write_to_fp(buffer)
    return buffer.getvalue()


def _get_language_code(lang: str) -> str:
    lang_map = {
        "urdu": "ur",
        "ur": "ur",
        "english": "en",
        "en": "en",
        "hindi": "hi",
        "hi": "hi",
    }
    return lang_map.get(lang.lower(), "en")


async def synthesize(text: str, language: str, index: int) -> dict:
    lang_code = _get_language_code(language)
    audio_bytes: bytes

    if settings.tts_provider == "elevenlabs" and settings.elevenlabs_api_key:
        try:
            audio_bytes = await asyncio.to_thread(_elevenlabs_synthesize_blocking, text, lang_code)
        except Exception:
            logger.warning("ElevenLabs TTS failed, falling back to gTTS", exc_info=True)
            audio_bytes = await asyncio.to_thread(_gtts_synthesize_blocking, text, lang_code)
    else:
        audio_bytes = await asyncio.to_thread(_gtts_synthesize_blocking, text, lang_code)

    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
    return {
        "audio": audio_base64,
        "format": "mp3",
        "lang": lang_code,
        "index": index,
    }


def _elevenlabs_synthesize_blocking(text: str, lang_code: str) -> bytes:
    from elevenlabs.client import ElevenLabs

    global _elevenlabs_client
    if _elevenlabs_client is None:
        _elevenlabs_client = ElevenLabs(api_key=settings.elevenlabs_api_key)
    voice_id = "21m00Tcm4TlvDq8ikWAM"
    if lang_code == "ur":
        voice_id = "OD2kz7M7Qb0GkClY7F9i"
    audio_generator = _elevenlabs_client.generate(
        text=text,
        voice=voice_id,
        model="eleven_multilingual_v2",
    )
    return b"".join(audio_generator)
