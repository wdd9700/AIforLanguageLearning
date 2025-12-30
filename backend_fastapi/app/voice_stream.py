from __future__ import annotations

import asyncio
import base64
import os
import time
import warnings
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class VoiceStreamConfig:
    sample_rate: int = 16000
    channels: int = 1
    encoding: str = "pcm_s16le"
    partial_emit_interval_ms: int = 800
    language: str | None = None

    # VAD (optional): if enabled, detect end-of-utterance by sustained silence.
    vad_enabled: bool = False
    vad_mode: int = 2
    vad_silence_ms: int = 800
    vad_frame_ms: int = 20


class VoiceStream:
    """最小可用的“直播式音频上传”会话缓冲器。

    说明：
    - 前端负责切片并通过 WS 发送音频 chunk（base64）
    - 后端负责缓冲，并周期性触发 ASR 产生 partial/final
    - 这里不强绑定具体 ASR 引擎：可注入 transcriber；缺省走降级输出
    """

    def __init__(
        self,
        *,
        config: VoiceStreamConfig,
        transcriber: Optional[Callable[[bytes, VoiceStreamConfig], str]] = None,
    ) -> None:
        self.config = config
        self._transcriber = transcriber
        self._buffer = bytearray()
        self._last_partial_ts_ms: int = 0
        self._lock = asyncio.Lock()

        self._vad = None
        self._vad_remainder = bytearray()
        self._vad_speech_seen = False
        self._vad_silence_ms = 0
        self._vad_should_finalize = False

        if bool(self.config.vad_enabled):
            try:
                import webrtcvad  # type: ignore

                mode = int(self.config.vad_mode)
                if mode < 0:
                    mode = 0
                if mode > 3:
                    mode = 3
                self._vad = webrtcvad.Vad(mode)
            except Exception:
                # VAD is optional; if dependency missing or init fails, keep disabled.
                self._vad = None

    async def add_chunk_b64(self, data_b64: str) -> int:
        raw = base64.b64decode(data_b64.encode("utf-8")) if data_b64 else b""
        return await self.add_chunk_bytes(raw)

    async def add_chunk_bytes(self, raw: bytes) -> int:
        async with self._lock:
            if raw:
                self._buffer.extend(raw)
                self._feed_vad_locked(raw)
            return len(self._buffer)

    def vad_should_finalize(self) -> bool:
        return bool(self._vad_should_finalize)

    def _feed_vad_locked(self, raw: bytes) -> None:
        if not bool(self.config.vad_enabled):
            return
        if not raw:
            return

        # Only support 16kHz mono pcm_s16le for VAD in P1.
        if self.config.encoding != "pcm_s16le":
            return
        if self.config.sample_rate != 16000:
            return
        if self.config.channels != 1:
            return

        frame_ms = int(self.config.vad_frame_ms) or 20
        if frame_ms not in (10, 20, 30):
            frame_ms = 20

        frame_bytes = int(16000 * (frame_ms / 1000.0) * 2)  # int16
        if frame_bytes <= 0:
            return

        self._vad_remainder.extend(raw)
        while len(self._vad_remainder) >= frame_bytes:
            frame = bytes(self._vad_remainder[:frame_bytes])
            del self._vad_remainder[:frame_bytes]

            # VAD 判定（优先 webrtcvad，若不可用/不可靠则用能量阈值兜底）。
            is_speech = False
            if self._vad is not None:
                try:
                    is_speech = bool(self._vad.is_speech(frame, 16000))
                except Exception:
                    is_speech = False

            if not is_speech:
                # Energy-based fallback: treat any non-trivial amplitude as speech.
                # This makes auto-end work reliably for “speech + trailing zeros”.
                import array

                samples = array.array("h")
                samples.frombytes(frame)
                peak = 0
                for s in samples:
                    a = -s if s < 0 else s
                    if a > peak:
                        peak = a
                is_speech = peak > 200

            if is_speech:
                self._vad_speech_seen = True
                self._vad_silence_ms = 0
            else:
                if self._vad_speech_seen:
                    self._vad_silence_ms += frame_ms
                    if self._vad_silence_ms >= int(self.config.vad_silence_ms):
                        self._vad_should_finalize = True

    async def maybe_transcribe_partial(self) -> Optional[str]:
        now_ms = int(time.time() * 1000)
        if now_ms - self._last_partial_ts_ms < self.config.partial_emit_interval_ms:
            return None

        async with self._lock:
            if not self._buffer:
                return None
            audio = bytes(self._buffer)

        self._last_partial_ts_ms = now_ms
        text = await self._transcribe(audio)
        if text:
            return text
        return None

    async def transcribe_final(self) -> str:
        async with self._lock:
            audio = bytes(self._buffer)

        text = await self._transcribe(audio)
        return text

    async def _transcribe(self, audio: bytes) -> str:
        if not audio:
            return ""

        if self._transcriber is None:
            return "（ASR 未启用）"

        # transcriber 是同步 CPU 计算（faster-whisper / whisper），必须放到线程池里跑，
        # 否则会阻塞事件循环导致 websocket backpressure（客户端 send 卡住）。
        res = await asyncio.to_thread(self._transcriber, audio, self.config)
        return (res or "").strip()


def try_create_faster_whisper_transcriber(
    *,
    model_name: str = "small",
    device: str = "cpu",
    compute_type: str = "int8",
) -> Optional[Callable[[bytes, VoiceStreamConfig], str]]:
    """可选的 faster-whisper 适配（未安装则返回 None）。

    注意：真正低延迟流式需要更复杂的增量解码；这里作为 P0 可用实现。
    """

    # 尽量避免 third-party 包输出进度条/告警污染后端输出（尤其在集成测试里）。
    os.environ.setdefault("TQDM_DISABLE", "1")
    warnings.filterwarnings(
        "ignore",
        message=r"pkg_resources is deprecated as an API\..*",
        category=UserWarning,
    )
    warnings.filterwarnings(
        "ignore",
        category=UserWarning,
        module=r"ctranslate2(\..*)?",
    )

    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception:
        return None

    import numpy as np
    import threading

    # 选择轻量模型，避免本地桌面环境过重；用户可自行替换
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    model_lock = threading.Lock()

    def _transcribe(audio: bytes, cfg: VoiceStreamConfig) -> str:
        # 假设前端已按 cfg 提供 16k/mono/pcm_s16le。
        if cfg.encoding != "pcm_s16le":
            return "（ASR 不支持的编码）"
        if cfg.channels != 1:
            return "（ASR 仅支持单声道）"

        # int16 PCM -> float32 [-1, 1]
        pcm = np.frombuffer(audio, dtype=np.int16)
        if pcm.size == 0:
            return ""
        audio_f32 = pcm.astype(np.float32) / 32768.0

        with model_lock:
            segments, _info = model.transcribe(
                audio_f32,
                language=cfg.language,
                vad_filter=True,
                beam_size=1,
            )
        text_parts = []
        for seg in segments:
            t = (getattr(seg, "text", "") or "").strip()
            if t:
                text_parts.append(t)
        return " ".join(text_parts).strip()

    return _transcribe


def try_create_openai_whisper_transcriber(
    *,
    model_name: str = "small",
    device: str = "cpu",
) -> Optional[Callable[[bytes, VoiceStreamConfig], str]]:
    """可选的 openai-whisper（whisper）适配：未安装则返回 None。"""

    try:
        import numpy as np
        import whisper  # type: ignore
    except Exception:
        return None

    model = whisper.load_model(model_name, device=device)

    def _transcribe(audio: bytes, cfg: VoiceStreamConfig) -> str:
        if cfg.encoding != "pcm_s16le":
            return "（ASR 不支持的编码）"
        if cfg.channels != 1:
            return "（ASR 仅支持单声道）"

        pcm = np.frombuffer(audio, dtype=np.int16)
        if pcm.size == 0:
            return ""
        audio_f32 = pcm.astype(np.float32) / 32768.0

        # whisper 期望 16kHz
        if cfg.sample_rate != 16000:
            return "（ASR 仅支持 16kHz）"

        options: dict[str, Any] = {}
        if cfg.language:
            options["language"] = cfg.language

        result = model.transcribe(audio_f32, **options)  # type: ignore[arg-type]
        text = (result or {}).get("text")
        return (text or "").strip() if isinstance(text, str) else ""

    return _transcribe
