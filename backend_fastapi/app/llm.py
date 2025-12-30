from __future__ import annotations

import asyncio
import json
from typing import Any
from typing import AsyncIterator
from typing import Literal

import httpx

from .prompts import render_prompt
from .settings import settings


async def generate_definition(term: str) -> str:
    """尽力从 LM Studio（OpenAI 兼容）生成一个简短释义。

    约束：
    - 不能依赖 LLM 一定可用（本地服务可能未启动）
    - 超时要短，失败要快速降级
    """

    prompt = (
        "你是一个外语学习助手。请用简洁中文解释这个英文词/短语，并给一个例句。\n"
        f"词：{term}\n"
        "输出格式：\n释义：...\n例句：..."
    )

    payload: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    timeout = httpx.Timeout(settings.llm_timeout_seconds)

    try:
        async with httpx.AsyncClient(base_url=settings.llm_base_url, timeout=timeout) as client:
            resp = await client.post(
                "/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            # OpenAI 兼容：choices[0].message.content
            content = data.get("choices", [{}])[0].get("message", {}).get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
    except Exception:
        # 降级：不抛出，保持服务可用
        return "释义：暂无（LLM 未连接或超时）\n例句：暂无"

    return "释义：暂无\n例句：暂无"


async def chat_complete(*, system_prompt: str, user_text: str) -> str:
    """Generate a single-turn chat completion using an explicit system prompt.

    Used by voice dialogue. Must be resilient: failures should degrade quickly.
    """

    sp = (system_prompt or "").strip() or "You are a helpful assistant."
    ut = (user_text or "").strip()
    if not ut:
        return "（未检测到语音内容）"

    payload: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": sp},
            {"role": "user", "content": ut},
        ],
        "temperature": 0.4,
    }

    timeout = httpx.Timeout(settings.llm_timeout_seconds)

    try:
        async with httpx.AsyncClient(base_url=settings.llm_base_url, timeout=timeout) as client:
            resp = await client.post(
                "/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
    except Exception:
        return "（LLM 未连接或超时）"

    return "（LLM 输出为空）"


SSEEvent = tuple[Literal["data", "done"], str]


def _parse_openai_sse_line(line: str) -> SSEEvent | None:
    """Parse a single SSE line from OpenAI-compatible streaming.

    Expected shapes:
    - 'data: {json...}'
    - 'data: [DONE]'
    - empty / keep-alive lines
    """

    s = (line or "").strip()
    if not s:
        return None

    if not s.startswith("data:"):
        return None

    payload = s.removeprefix("data:").strip()
    if not payload:
        return None

    if payload == "[DONE]":
        return ("done", "")
    return ("data", payload)


def _extract_delta_text(obj: Any) -> str:
    """Extract delta text from OpenAI-compatible chat.completions streaming JSON."""

    if not isinstance(obj, dict):
        return ""

    choices = obj.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""

    c0 = choices[0] if isinstance(choices[0], dict) else {}

    # OpenAI ChatCompletions stream uses choices[].delta.content
    delta = c0.get("delta")
    if isinstance(delta, dict):
        content = delta.get("content")
        if isinstance(content, str):
            return content

    # Some servers may stream 'message.content'
    msg = c0.get("message")
    if isinstance(msg, dict):
        content = msg.get("content")
        if isinstance(content, str):
            return content

    return ""


async def stream_definition(term: str) -> AsyncIterator[str]:
    """Stream a definition from LM Studio, yielding incremental text deltas.

    Notes:
    - Uses OpenAI-compatible '/chat/completions' with stream=true.
    - On failure, yields nothing (caller should fall back).
    """

    prompt = (
        "你是一个外语学习助手。请用简洁中文解释这个英文词/短语，并给一个例句。\n"
        f"词：{term}\n"
        "输出格式：\n释义：...\n例句：..."
    )

    payload: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "stream": True,
    }


async def stream_chat(*, system_prompt: str, user_text: str) -> AsyncIterator[str]:
    """Stream a single-turn chat completion with an explicit system prompt.

    Yields incremental deltas; on failure yields nothing (caller should fall back).
    """

    sp = (system_prompt or "").strip() or "You are a helpful assistant."
    ut = (user_text or "").strip()
    if not ut:
        return

    payload: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": sp},
            {"role": "user", "content": ut},
        ],
        "temperature": 0.4,
        "stream": True,
    }

    timeout = httpx.Timeout(settings.llm_timeout_seconds)

    try:
        async with httpx.AsyncClient(base_url=settings.llm_base_url, timeout=timeout) as client:
            async with client.stream(
                "POST",
                "/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    evt = _parse_openai_sse_line(line)
                    if evt is None:
                        continue
                    kind, raw = evt
                    if kind == "done":
                        break
                    try:
                        obj = json.loads(raw)
                    except Exception:
                        continue
                    delta = _extract_delta_text(obj)
                    if delta:
                        yield delta
    except Exception:
        return

    timeout = httpx.Timeout(settings.llm_timeout_seconds)

    try:
        async with httpx.AsyncClient(base_url=settings.llm_base_url, timeout=timeout) as client:
            async with client.stream(
                "POST",
                "/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json=payload,
            ) as resp:
                resp.raise_for_status()

                async for line in resp.aiter_lines():
                    evt = _parse_openai_sse_line(line)
                    if evt is None:
                        continue

                    kind, raw = evt
                    if kind == "done":
                        break

                    try:
                        obj = json.loads(raw)
                    except Exception:
                        continue

                    delta = _extract_delta_text(obj)
                    if delta:
                        yield delta
    except asyncio.CancelledError:
        raise
    except Exception:
        return


def _extract_json_object(text: str) -> str:
    s = (text or "").strip()
    if not s:
        return ""
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return ""
    return s[start : end + 1]


def _fallback_essay_result(*, ocr_text: str, language: str) -> dict[str, Any]:
    return {
        "score": 60,
        "feedback": "（降级）未连接到 LLM，返回最小可用批改结果。",
        "errors": [],
        "suggestions": ["检查拼写与标点", "尽量使用更具体的词汇"],
        "rewritten": ocr_text.strip()[:2000],
        "language": language,
    }


def _normalize_essay_result(obj: Any, *, ocr_text: str, language: str) -> dict[str, Any]:
    if not isinstance(obj, dict):
        return _fallback_essay_result(ocr_text=ocr_text, language=language)

    try:
        score_raw = obj.get("score", 60)
        if score_raw is None:
            score_raw = 60
        score = int(score_raw)
    except Exception:
        score = 60
    score = max(0, min(100, score))

    feedback = obj.get("feedback")
    if not isinstance(feedback, str):
        feedback = ""

    errors = obj.get("errors")
    if not isinstance(errors, list):
        errors = []

    suggestions = obj.get("suggestions")
    if not isinstance(suggestions, list):
        suggestions = []

    rewritten = obj.get("rewritten")
    if not isinstance(rewritten, str):
        rewritten = ocr_text.strip()

    return {
        "score": score,
        "feedback": feedback,
        "errors": errors,
        "suggestions": suggestions,
        "rewritten": rewritten,
        "language": language,
    }


async def grade_essay(*, ocr_text: str, language: str) -> dict[str, Any]:
    """作文批改：尽力调用 LLM；失败则返回可用的降级 JSON。"""

    prompt = render_prompt("essay_grade.j2", language=language, ocr_text=ocr_text)

    payload: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }

    timeout = httpx.Timeout(settings.llm_timeout_seconds)

    try:
        async with httpx.AsyncClient(base_url=settings.llm_base_url, timeout=timeout) as client:
            resp = await client.post(
                "/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content")
            if isinstance(content, str) and content.strip():
                json_text = _extract_json_object(content)
                if json_text:
                    obj = json.loads(json_text)
                    return _normalize_essay_result(obj, ocr_text=ocr_text, language=language)
    except Exception:
        return _fallback_essay_result(ocr_text=ocr_text, language=language)

    return _fallback_essay_result(ocr_text=ocr_text, language=language)
