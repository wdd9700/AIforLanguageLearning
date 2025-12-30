from __future__ import annotations

import io
import os
import tempfile
import threading
import wave

from .settings import settings


def synthesize_wav_silence(
    text: str,
    *,
    sample_rate: int = 16000,
    channels: int = 1,
) -> bytes:
    """Minimal TTS placeholder: returns a WAV of silence.

    This keeps the WS protocol stable (TTS_CHUNK/TTS_RESULT) without requiring
    external TTS runtimes.
    """

    # Duration heuristic: small but non-zero to allow chunking in tests.
    n = len((text or "").strip())
    seconds = 0.25 + min(2.0, n * 0.01)
    frames = max(1, int(sample_rate * seconds))

    # 16-bit PCM silence.
    silence = b"\x00\x00" * frames * channels

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(int(channels))
        wf.setsampwidth(2)
        wf.setframerate(int(sample_rate))
        wf.writeframes(silence)

    return buf.getvalue()


def synthesize_tts_wav(text: str) -> bytes:
    """Synthesize TTS audio as a single WAV bytes blob.

    - Default: silence WAV (no external deps)
    - Optional: XTTS v2 (Coqui TTS)
    """

    backend = (settings.tts_backend or "silence").strip().lower()
    if backend in ("silence", "none", "stub"):
        return synthesize_wav_silence(text)

    if backend in ("xtts", "xtts_v2"):
        try:
            return _synthesize_xtts_wav(text)
        except Exception:
            # Fail-safe: never crash the WS session because of optional TTS.
            return synthesize_wav_silence(text)

    # Unknown backend -> safe fallback.
    return synthesize_wav_silence(text)


_xtts_lock = threading.Lock()
_xtts_tts = None


def _get_xtts_tts():
    global _xtts_tts
    with _xtts_lock:
        if _xtts_tts is not None:
            return _xtts_tts

        # Optional deps; will raise ImportError if not installed.
        os.environ.setdefault("PYTORCH_FAKE_TENSOR_ENABLED", "0")
        os.environ.setdefault("TORCH_LOGS", "-fake_tensor")
        os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

        from TTS.api import TTS  # type: ignore

        model_name = (settings.xtts_model_name or "").strip() or "tts_models/multilingual/multi-dataset/xtts_v2"
        tts = TTS(model_name)

        # Choose device automatically.
        try:
            import torch  # type: ignore

            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            device = "cpu"

        _xtts_tts = tts.to(device)
        return _xtts_tts


def _synthesize_xtts_wav(text: str) -> bytes:
    """XTTS v2 -> WAV bytes.

    Uses tts_to_file then reads bytes back; this matches the proven wrapper
    approach in this repo and avoids some XTTS API quirks.
    """

    prompt = (settings.xtts_prompt_wav or "").strip() or os.getenv("XTTS_PROMPT_WAV", "")
    if not prompt or not os.path.exists(prompt):
        raise FileNotFoundError("XTTS prompt wav not found; set AIFL_XTTS_PROMPT_WAV")

    language = (settings.xtts_language or "en").strip() or "en"
    tts = _get_xtts_tts()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        tts.tts_to_file(
            text=text or "",
            speaker_wav=prompt,
            language=language,
            file_path=tmp_path,
        )
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
