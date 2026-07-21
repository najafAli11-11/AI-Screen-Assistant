import asyncio
import base64
import binascii
import logging
from collections.abc import Awaitable, Callable

from app.core.config import SUPPORTED_LANGUAGES, settings
from app.schemas import ErrorEvent
from app.services.session_store import Session


logger = logging.getLogger(__name__)
Emit = Callable[[str, dict[str, object]], Awaitable[None]]


class ClientInputError(ValueError):
    def __init__(self, code: str, message: str, retryable: bool = True) -> None:
        super().__init__(message)
        self.event = ErrorEvent(code=code, message=message, retryable=retryable)


def decode_base64_payload(value: str, max_bytes: int, code: str, label: str) -> bytes:
    if not value:
        return b""
    # Reject oversized payloads before decoding (base64 inflates ~4/3).
    if len(value) > max_bytes * 4 // 3 + 8:
        raise ClientInputError(code, f"{label.capitalize()} payload is too large.", retryable=True)
    try:
        payload = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ClientInputError(code, f"Invalid {label} payload.", retryable=True) from exc
    if len(payload) > max_bytes:
        raise ClientInputError(code, f"{label.capitalize()} payload is too large.", retryable=True)
    return payload


def _validate_jpeg(frame_bytes: bytes) -> None:
    if len(frame_bytes) < 4 or frame_bytes[:2] != b"\xff\xd8":
        raise ClientInputError("CAP_002", "Screen frame is not a valid JPEG image.", retryable=True)


async def process_query(
    *,
    session: Session,
    frame_base64: str,
    audio_base64: str,
    emit: Emit,
) -> None:
    frame_bytes = decode_base64_payload(frame_base64, settings.max_frame_bytes, "CAP_002", "screen frame")
    audio_bytes = decode_base64_payload(audio_base64, settings.max_audio_bytes, "AUD_001", "audio")

    if not frame_bytes:
        raise ClientInputError("CAP_001", "Please re-share your screen to continue.", retryable=True)
    _validate_jpeg(frame_bytes)

    if audio_bytes:
        transcript, detected_lang, avg_logprob, is_confident = await _transcribe(audio_bytes, session.language)
        await emit(
            "transcript:ready",
            {
                "text": transcript,
                "lang": detected_lang,
                "avg_logprob": avg_logprob,
                "lowConfidence": not is_confident,
            },
        )
        if not transcript:
            raise ClientInputError("STT_002", "No speech detected. Please try again.", retryable=True)
    else:
        transcript = "What is on my screen and what should I do next?"
        detected_lang = session.language

    target_language = detected_lang if detected_lang in SUPPORTED_LANGUAGES else session.language
    await _stream_response(session, frame_base64, transcript, target_language, emit)


async def _transcribe(audio_bytes: bytes, language: str | None = None) -> tuple[str, str, float, bool]:
    from pipeline import stt as stt_pipeline

    try:
        stt_result = await asyncio.to_thread(
            stt_pipeline.transcribe,
            audio_bytes,
            settings.sample_rate,
            language if language in SUPPORTED_LANGUAGES else None,
        )
    except Exception as exc:
        logger.exception("Speech transcription failed")
        raise ClientInputError(
            "STT_001",
            "Sorry, I could not hear that clearly. Please try again.",
            retryable=True,
        ) from exc

    transcript = stt_result.get("text", "").strip()
    detected_lang = stt_result.get("language", "en")
    avg_logprob = float(stt_result.get("avg_logprob", -2.0))
    return transcript, detected_lang, avg_logprob, stt_pipeline.is_high_confidence(stt_result)


async def _stream_response(
    session: Session,
    frame_base64: str,
    user_query: str,
    target_language: str,
    emit: Emit,
) -> None:
    from pipeline import llm as llm_pipeline
    from pipeline import sentence_splitter

    sentence_buffer = ""
    sentence_index = 0
    full_response = ""
    # TTS runs concurrently with LLM streaming so audio for sentence N is
    # generated while sentence N+1 is still being written. Ordered playback is
    # guaranteed by the per-sentence index, which clients use to queue audio.
    audio_tasks: list[asyncio.Task] = []

    def schedule_audio(sentence: str) -> None:
        nonlocal sentence_index
        sentence = sentence.strip()
        if not sentence:
            return
        audio_tasks.append(
            asyncio.create_task(
                _emit_sentence_audio(sentence, sentence_index, session.session_id, target_language, emit)
            )
        )
        sentence_index += 1

    try:
        async for token in llm_pipeline.stream_guidance(
            screenshot_base64=frame_base64,
            user_query=user_query,
            language=target_language,
            session_context=session.context_window,
        ):
            full_response += token
            sentence_buffer += token
            await emit("response:token", {"token": token, "sessionId": session.session_id})

            if sentence_splitter.is_sentence_complete(sentence_buffer):
                for sentence in sentence_splitter.split_sentences(sentence_buffer):
                    schedule_audio(sentence)
                sentence_buffer = ""
    except ValueError as exc:
        _cancel_tasks(audio_tasks)
        logger.warning("Assistant pipeline is not fully configured: %s", exc)
        raise ClientInputError(
            "CFG_001",
            "The assistant backend is missing required provider configuration.",
            retryable=False,
        ) from exc
    except ClientInputError:
        _cancel_tasks(audio_tasks)
        raise
    except Exception as exc:
        _cancel_tasks(audio_tasks)
        logger.exception("LLM streaming failed")
        raise ClientInputError(
            "LLM_001",
            "I need a moment. Please try again.",
            retryable=True,
        ) from exc

    if sentence_buffer.strip():
        schedule_audio(sentence_buffer)

    if audio_tasks:
        await asyncio.gather(*audio_tasks, return_exceptions=True)

    session.add_exchange(user_query, full_response.strip())
    await emit(
        "response:done",
        {
            "sessionId": session.session_id,
            "totalTokens": len(full_response.split()),
            "totalSentences": sentence_index,
        },
    )


def _cancel_tasks(tasks: list[asyncio.Task]) -> None:
    for task in tasks:
        task.cancel()


async def _emit_sentence_audio(
    sentence: str,
    index: int,
    session_id: str,
    target_language: str,
    emit: Emit,
) -> None:
    from pipeline import translate as translate_pipeline
    from pipeline import tts as tts_pipeline

    await emit("response:sentence", {"sentence": sentence, "index": index, "sessionId": session_id})
    final_sentence = sentence
    try:
        if translate_pipeline.needs_translation(sentence, target_language):
            final_sentence = await asyncio.to_thread(translate_pipeline.translate, sentence, target_language)
    except Exception:
        logger.warning("Translation fallback failed", exc_info=True)

    try:
        audio_data = await tts_pipeline.synthesize(final_sentence, target_language, index)
        await emit("response:audio", audio_data)
    except Exception:
        logger.warning("TTS generation failed for sentence %s", index, exc_info=True)
        await emit(
            "error:occurred",
            {
                "code": "TTS_001",
                "message": "Caption shown. Audio is temporarily unavailable.",
                "retryable": True,
            },
        )
