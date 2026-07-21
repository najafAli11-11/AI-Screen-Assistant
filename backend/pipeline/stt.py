import io
import threading
import wave
from typing import Optional

import numpy as np

from config import settings


_model = None
_model_lock = threading.Lock()
# Whisper models are not safe for concurrent inference; serialise transcribe calls.
_inference_lock = threading.Lock()


def _load_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                import whisper

                _model = whisper.load_model(settings.whisper_model)
    return _model


def preload() -> None:
    """Warm the Whisper model so the first user query is not delayed."""
    _load_model()


def transcribe(audio_bytes: bytes, sample_rate: int = 16000, language: Optional[str] = None) -> dict:
    audio_np = _audio_bytes_to_np(audio_bytes, sample_rate)
    if audio_np.size == 0 or float(np.max(np.abs(audio_np))) < 1e-4:
        # Pure silence: skip inference entirely, Whisper hallucinates on silence.
        return {"text": "", "language": "unknown", "avg_logprob": -2.0, "segments": []}

    model = _load_model()
    with _inference_lock:
        # Hinting the session language skips Whisper's per-clip language
        # detection, which misfires on short clips and non-native accents.
        result = model.transcribe(audio_np, language=language, task="transcribe", fp16=False)

    segments = result.get("segments", [])
    avg_logprob = -2.0
    if segments:
        avg_logprob = float(np.mean([s.get("avg_logprob", 0.0) for s in segments]))
    return {
        "text": result.get("text", "").strip(),
        "language": result.get("language", "unknown"),
        "avg_logprob": avg_logprob,
        "segments": [
            {
                "text": s["text"],
                "avg_logprob": s.get("avg_logprob", 0.0),
                "start": s.get("start", 0),
                "end": s.get("end", 0),
            }
            for s in segments
        ],
    }


def _audio_bytes_to_np(audio_bytes: bytes, target_sr: int) -> np.ndarray:
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
            sr = wf.getframerate()
            channels = wf.getnchannels()
            frames = wf.readframes(wf.getnframes())
            audio_np = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            if channels > 1:
                audio_np = audio_np.reshape(-1, channels).mean(axis=1)
            if sr != target_sr and len(audio_np):
                from scipy.signal import resample

                audio_np = resample(audio_np, int(len(audio_np) * target_sr / sr)).astype(np.float32)
            return audio_np
    except Exception:
        # Fall back to treating the payload as raw 16-bit PCM at target rate.
        audio_np = np.frombuffer(audio_bytes[: len(audio_bytes) // 2 * 2], dtype=np.int16).astype(np.float32) / 32768.0
        return audio_np


def is_high_confidence(result: dict, threshold: Optional[float] = None) -> bool:
    t = threshold if threshold is not None else settings.stt_confidence_threshold
    return result.get("avg_logprob", -2.0) > t
