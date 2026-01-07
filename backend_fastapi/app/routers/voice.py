from __future__ import annotations

import base64

from fastapi import APIRouter
from pydantic import BaseModel

from ..prompts import render_prompt
from ..tts import synthesize_tts_wav

router = APIRouter(prefix="/api/voice", tags=["voice"])


class GeneratePromptRequest(BaseModel):
    scenario: str
    language: str


class GeneratePromptResponse(BaseModel):
    success: bool
    systemPrompt: str


@router.post("/generate-prompt", response_model=GeneratePromptResponse)
async def generate_prompt(req: GeneratePromptRequest) -> GeneratePromptResponse:
    scenario = (req.scenario or "").strip()
    language = (req.language or "").strip()

    # 最小可用：不依赖 LLM 可用性，直接用模板生成 system prompt。
    # 前端会允许用户在 review step 里编辑。
    system_prompt = render_prompt("voice_system_prompt.j2", scenario=scenario, language=language)

    return GeneratePromptResponse(success=True, systemPrompt=system_prompt)


class StartSessionRequest(BaseModel):
    systemPrompt: str


class StartSessionResponse(BaseModel):
    success: bool
    openingText: str
    openingAudio: str


@router.post("/start", response_model=StartSessionResponse)
async def start_session(req: StartSessionRequest) -> StartSessionResponse:
    system_prompt = (req.systemPrompt or "").strip()

    # 为了兼容现有前端流程，返回固定开场白；同时生成可播放的 openingAudio。
    # openingAudio: base64(wav bytes)。默认 TTS 后端是 silence（仍是“真实音频”，只是静音）。
    if system_prompt:
        opening_text = "好的，我们开始练习吧。你可以先说一句话。"
    else:
        opening_text = "我们开始吧。你可以先说一句话。"

    wav = synthesize_tts_wav(opening_text)
    opening_audio_b64 = base64.b64encode(wav).decode("utf-8") if wav else ""
    return StartSessionResponse(success=True, openingText=opening_text, openingAudio=opening_audio_b64)
