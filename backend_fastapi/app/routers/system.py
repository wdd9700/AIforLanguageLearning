from __future__ import annotations

import importlib
import sys
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from ..settings import settings

router = APIRouter(prefix="/api/system", tags=["system"])


class SystemConfig(BaseModel):
    port: int
    llmEndpoint: str
    models: dict[str, Any]
    prompts: dict[str, Any]
    ocr: dict[str, Any]
    tts: dict[str, Any]
    asr: dict[str, Any]
    python: dict[str, Any]


class SystemConfigResponse(BaseModel):
    success: bool
    data: SystemConfig


@router.get("/config", response_model=SystemConfigResponse)
async def get_config() -> SystemConfigResponse:
    # P0：返回前端期待的结构化字段；目前不做持久化配置面板，只做运行态回显。
    def _has_module(module_name: str) -> bool:
        try:
            importlib.import_module(module_name)
            return True
        except Exception:
            return False

    has_faster_whisper = _has_module("faster_whisper")
    has_openai_whisper = _has_module("whisper")

    cfg = SystemConfig(
        port=int(settings.port),
        llmEndpoint=str(settings.llm_base_url),
        models={"default": str(settings.llm_model)},
        prompts={},
        ocr={},
        tts={"backend": str(settings.tts_backend)},
        asr={
            "enabled": bool(settings.enable_asr),
            "backend": str(settings.asr_backend),
            "model": str(settings.asr_model),
            "device": str(settings.asr_device),
            "computeType": str(settings.asr_compute_type),
            "runtime": {
                "available": bool(has_faster_whisper or has_openai_whisper),
                "hasFasterWhisper": bool(has_faster_whisper),
                "hasOpenAIWhisper": bool(has_openai_whisper),
            },
        },
        python={
            "executable": str(sys.executable),
            "version": str(sys.version).split(" ")[0],
        },
    )
    return SystemConfigResponse(success=True, data=cfg)


@router.post("/config")
async def update_config(_: dict[str, Any]) -> dict[str, Any]:
    # P0：前端会调用该接口保存系统配置；当前 FastAPI 版不做持久化，先返回 success。
    return {"success": True}
