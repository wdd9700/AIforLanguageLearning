from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(
        default="development", validation_alias=AliasChoices("AIFL_APP_ENV", "APP_ENV")
    )
    port: int = Field(default=8012, validation_alias=AliasChoices("AIFL_PORT", "PORT"))

    # LM Studio (OpenAI compatible)
    llm_base_url: str = Field(
        default="http://127.0.0.1:1234/v1",
        validation_alias=AliasChoices("AIFL_LLM_BASE_URL", "LLM_BASE_URL"),
    )
    llm_api_key: str = Field(
        default="lm-studio", validation_alias=AliasChoices("AIFL_LLM_API_KEY", "LLM_API_KEY")
    )

    llm_model: str = Field(
        default="local-model", validation_alias=AliasChoices("AIFL_LLM_MODEL", "LLM_MODEL")
    )
    llm_timeout_seconds: float = Field(
        default=30.0,
        validation_alias=AliasChoices("AIFL_LLM_TIMEOUT_SECONDS", "LLM_TIMEOUT_SECONDS"),
    )

    # DB
    database_url: str = Field(
        default="sqlite:///./data/app.db",
        validation_alias=AliasChoices("AIFL_DATABASE_URL", "DATABASE_URL"),
    )

    # Voice (P0): 默认开启；若运行环境缺少 ASR 依赖，会降级为“ASR 后端不可用”的提示文本。
    enable_asr: bool = Field(
        default=True, validation_alias=AliasChoices("AIFL_ENABLE_ASR", "ENABLE_ASR")
    )
    asr_backend: str = Field(
        default="faster-whisper",
        validation_alias=AliasChoices("AIFL_ASR_BACKEND", "ASR_BACKEND"),
    )
    asr_model: str = Field(
        default="small", validation_alias=AliasChoices("AIFL_ASR_MODEL", "ASR_MODEL")
    )
    asr_device: str = Field(
        default="cpu", validation_alias=AliasChoices("AIFL_ASR_DEVICE", "ASR_DEVICE")
    )
    asr_compute_type: str = Field(
        default="int8",
        validation_alias=AliasChoices("AIFL_ASR_COMPUTE_TYPE", "ASR_COMPUTE_TYPE"),
    )

    # Voice WS: 请求级别空闲超时（秒）；防止客户端未发送 AUDIO_END 导致会话长期占用。
    voice_request_idle_seconds: int = 30

    # Voice VAD（P1）：停顿判定，支持“无需客户端发送 AUDIO_END 也能自动收句”。
    enable_vad: bool = Field(default=False, validation_alias=AliasChoices("AIFL_ENABLE_VAD", "ENABLE_VAD"))
    vad_mode: int = Field(default=2, validation_alias=AliasChoices("AIFL_VAD_MODE", "VAD_MODE"))
    vad_silence_ms: int = Field(
        default=800,
        validation_alias=AliasChoices("AIFL_VAD_SILENCE_MS", "VAD_SILENCE_MS"),
    )

    # TTS（P1）：默认占位静音 wav；生产可切到 XTTS。
    tts_backend: str = Field(
        default="silence",
        validation_alias=AliasChoices("AIFL_TTS_BACKEND", "TTS_BACKEND"),
    )
    tts_chunk_size_bytes: int = Field(
        default=16 * 1024,
        validation_alias=AliasChoices("AIFL_TTS_CHUNK_SIZE_BYTES", "TTS_CHUNK_SIZE_BYTES"),
    )

    # XTTS v2 (optional)
    xtts_model_name: str = Field(
        default="tts_models/multilingual/multi-dataset/xtts_v2",
        validation_alias=AliasChoices("AIFL_XTTS_MODEL_NAME", "XTTS_MODEL_NAME"),
    )
    xtts_prompt_wav: str = Field(
        default="",
        validation_alias=AliasChoices("AIFL_XTTS_PROMPT_WAV", "XTTS_PROMPT_WAV"),
    )
    xtts_language: str = Field(
        default="en",
        validation_alias=AliasChoices("AIFL_XTTS_LANGUAGE", "XTTS_LANGUAGE"),
    )


settings = Settings()
