from __future__ import annotations

import asyncio
import json
import re
from typing import Any
from typing import AsyncIterator
from typing import Literal

import httpx

from .prompts import render_prompt
from .settings import settings


_LLM_MODEL_CACHE: str | None = None
_LLM_MODEL_LOCK = asyncio.Lock()


def _extract_chat_response_text(data: Any) -> str:
    """Extract assistant text from an OpenAI-compatible chat.completions response.

    Some servers/models (notably certain "thinking" variants) may return an empty
    message.content while placing the actual text in message.reasoning_content.
    """

    if not isinstance(data, dict):
        return ""

    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""

    c0 = choices[0] if isinstance(choices[0], dict) else {}
    msg = c0.get("message")
    if not isinstance(msg, dict):
        return ""

    content = msg.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()

    # Some providers return content as structured parts.
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str) and part.strip():
                parts.append(part.strip())
            elif isinstance(part, dict):
                txt = part.get("text")
                if isinstance(txt, str) and txt.strip():
                    parts.append(txt.strip())
        if parts:
            return "\n".join(parts).strip()

    reasoning = msg.get("reasoning_content")
    if isinstance(reasoning, str) and reasoning.strip():
        return reasoning.strip()

    return ""


async def _resolve_llm_model(client: httpx.AsyncClient) -> str:
    """Resolve a usable model id for OpenAI-compatible servers.

    Problem:
    - settings.llm_model defaults to 'local-model', which is often NOT a real model id in LM Studio.
    - When the model id is invalid, LM calls fail and we degrade to fallback text.

    Strategy:
    - If user configured a non-placeholder model, use it.
    - Otherwise, query /models and pick the first returned id (cached).
    """

    configured = str(getattr(settings, "llm_model", "") or "").strip()
    if configured and configured != "local-model":
        return configured

    global _LLM_MODEL_CACHE
    if _LLM_MODEL_CACHE:
        return _LLM_MODEL_CACHE

    async with _LLM_MODEL_LOCK:
        if _LLM_MODEL_CACHE:
            return _LLM_MODEL_CACHE

        try:
            resp = await client.get(
                "/models",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            )
            resp.raise_for_status()
            data = resp.json()
            models = data.get("data")
            if isinstance(models, list) and models:
                def _score(model_id: str) -> tuple[int, str] | None:
                    mid = (model_id or "").strip()
                    if not mid:
                        return None
                    low = mid.lower()
                    # Exclude non-chat models.
                    if any(k in low for k in ("embedding", "whisper", "cosyvoice", "tts", "asr", "rerank")):
                        return None
                    # Prefer smaller parameter counts (e.g. 4b < 8b < 30b < 80b).
                    m = re.search(r"(\d+)\s*b\b", low)
                    size = int(m.group(1)) if m else 999
                    # De-prioritize vision-language variants for simple vocab.
                    if "vl" in low:
                        size += 200
                    # De-prioritize "thinking" variants that may hide output in reasoning_content.
                    if "thinking" in low:
                        size += 300
                    return (size, mid)

                best: tuple[int, str] | None = None
                for item in models:
                    if not isinstance(item, dict):
                        continue
                    mid = item.get("id")
                    if not isinstance(mid, str):
                        continue
                    score = _score(mid)
                    if score is None:
                        continue
                    if best is None or score < best:
                        best = score

                chosen = best[1] if best else None
                if not chosen:
                    # Fallback to first id.
                    first = models[0]
                    if isinstance(first, dict) and isinstance(first.get("id"), str):
                        chosen = str(first["id"]).strip()

                if chosen:
                    _LLM_MODEL_CACHE = chosen
                    return _LLM_MODEL_CACHE
        except Exception:
            pass

    # Last resort: use whatever is configured.
    return configured or "local-model"


def _extract_vocab_from_text(text: str) -> dict[str, Any]:
    s = (text or "").strip()
    if not s:
        return {"meaning": "", "example": "", "example_translation": "", "definitions": []}

    def _maybe_fix_keys(raw: str) -> str:
        t = (raw or "").strip()
        if not t:
            return t
        # Fix patterns like: {" "meaning": ...} or {"  "example": ...}
        t = re.sub(
            r'"\s*"(meaning|example|example_translation|exampleTranslation)"',
            r'"\1"',
            t,
        )
        return t

    def _try_parse_obj(raw: str) -> Any:
        t = (raw or "").strip()
        if not t:
            return None

        # Strip code fences if present.
        if t.startswith("```"):
            t = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", t)
            t = re.sub(r"\s*```\s*$", "", t).strip()

        # First attempt: direct JSON.
        try:
            return json.loads(t)
        except Exception:
            pass

        # If it looks like escaped JSON (e.g. {\"definitions\":...}), unescape quotes/backslashes.
        if "\\\"" in t and (t.startswith("{\\\"") or t.startswith("[\\\"")):
            candidate = t.replace("\\\"", '"').replace("\\\\", "\\")
            candidate = _maybe_fix_keys(candidate)
            try:
                return json.loads(candidate)
            except Exception:
                pass

        # Extract the largest {...} block and retry.
        if "{" in t and "}" in t:
            start = t.find("{")
            end = t.rfind("}")
            if 0 <= start < end:
                candidate = t[start : end + 1]
                candidate = _maybe_fix_keys(candidate)
                try:
                    return json.loads(candidate)
                except Exception:
                    pass

                # Retry after unescaping common patterns.
                if "\\\"" in candidate:
                    candidate2 = candidate.replace("\\\"", '"').replace("\\\\", "\\")
                    candidate2 = _maybe_fix_keys(candidate2)
                    try:
                        return json.loads(candidate2)
                    except Exception:
                        pass

        return None

    # Try JSON first.
    obj = _try_parse_obj(s)
    if isinstance(obj, str):
        # Double-decode if model returned a JSON string.
        obj2 = _try_parse_obj(obj)
        if obj2 is not None:
            obj = obj2

    if isinstance(obj, dict):
        defs = obj.get("definitions")
        if isinstance(defs, list):
            parsed_defs: list[dict[str, str]] = []
            for item in defs:
                if not isinstance(item, dict):
                    continue
                meaning = str(item.get("meaning") or item.get("definition") or "").strip()
                example = str(item.get("example") or item.get("example_en") or "").strip()
                example_translation = str(
                    item.get("example_translation")
                    or item.get("exampleTranslation")
                    or item.get("example_zh")
                    or ""
                ).strip()
                if meaning or example or example_translation:
                    parsed_defs.append(
                        {
                            "meaning": meaning,
                            "example": example,
                            "example_translation": example_translation,
                        }
                    )
            return {
                "meaning": str(obj.get("meaning") or obj.get("definition") or "").strip(),
                "example": "",
                "example_translation": "",
                "definitions": parsed_defs,
            }

        return {
            "meaning": str(obj.get("meaning") or obj.get("definition") or "").strip(),
            "example": str(obj.get("example") or obj.get("example_en") or "").strip(),
            "example_translation": str(
                obj.get("example_translation")
                or obj.get("exampleTranslation")
                or obj.get("example_zh")
                or ""
            ).strip(),
            "definitions": [],
        }

    # NOTE: JSON-in-text extraction is handled by _try_parse_obj above.

    def _clean_line(line: str) -> str:
        t = (line or "").strip()
        t = re.sub(r"^\s*(?:\d+\.|[-•]+)\s*", "", t)
        return t.strip()

    lines = [_clean_line(x) for x in s.splitlines() if _clean_line(x)]
    if len(lines) == 1:
        one = lines[0]
        # Split combined one-liners.
        one = re.sub(r"(例句翻译|例句|释义)\s*[:：]", r"\n\1：", one)
        lines = [_clean_line(x) for x in one.splitlines() if _clean_line(x)]

    meaning = ""
    example = ""
    example_translation = ""
    for line in lines:
        m = re.match(r"^释义\s*[:：]\s*(.+)$", line)
        if m:
            meaning = m.group(1).strip()
            continue

        m = re.match(r"^(?:例句翻译|翻译)\s*[:：]\s*(.+)$", line)
        if m:
            example_translation = m.group(1).strip()
            continue

        m = re.match(r"^例句\s*[:：]\s*(.+)$", line)
        if m:
            example = m.group(1).strip()
            continue

    if not (meaning or example or example_translation):
        meaning = s

    return {"meaning": meaning, "example": example, "example_translation": example_translation, "definitions": []}


async def generate_vocab_fields(term: str) -> dict[str, Any]:
    """Generate structured vocab fields via LM Studio (OpenAI compatible).

    Returns keys:
    - meaning (zh)
    - example (en)
    - example_translation (zh)

    Must be resilient: LLM may be unavailable or output non-JSON.
    """

    t = (term or "").strip()
    if not t:
        return {"meaning": "", "example": "", "example_translation": "", "definitions": []}

    def _should_expand(term_text: str) -> bool:
        low = (term_text or "").strip().lower()
        if not low:
            return False
        # Phrases usually have one primary meaning.
        if " " in low:
            return False
        # Heuristic: very short/common function words and classic polysemy verbs.
        common = {
            "to",
            "in",
            "on",
            "at",
            "for",
            "as",
            "by",
            "up",
            "down",
            "over",
            "set",
            "run",
            "get",
            "make",
            "take",
            "go",
            "come",
            "put",
            "turn",
            "right",
            "left",
            "like",
            "can",
            "will",
            "may",
        }
        return len(low) <= 3 or low in common

    prompt = (
        "你是一个外语学习助手。请为给定英文词/短语生成结构化结果。\n"
        f"term: {t}\n"
        "要求：\n"
        "- 如果确实有多个常用义项/用法，请返回多个义项（不必强行凑数）。\n"
        "- 每条义项都要有：meaning(中文释义)、example(英文例句)、example_translation(中文翻译)。\n"
        "- meaning 要简洁但完整（可以包含 1-2 个短语解释/用法提示）。\n"
        "- 只输出一个 JSON 对象，不要输出任何多余文本/Markdown/代码块。\n"
        'JSON schema: {"definitions":[{"meaning":"...","example":"...","example_translation":"..."}, ...]}'
    )

    expand_prompt = (
        "你是一个外语学习助手。请为给定英文词生成更全面的多义项解释。\n"
        f"term: {t}\n"
        "要求：\n"
        "- 给出尽可能多的常见义项/用法（优先常用、真实；不要生造冷门）。\n"
        "- 对于像 to/in/on/at 这类介词/功能词：给出多个最常用的用法，并各配一个英文例句与中文翻译。\n"
        "- 每条义项都要有：meaning(中文释义)、example(英文例句)、example_translation(中文翻译)。\n"
        "- 只输出一个 JSON 对象，不要输出任何多余文本/Markdown/代码块。\n"
        'JSON schema: {"definitions":[{"meaning":"...","example":"...","example_translation":"..."}, ...]}'
    )

    # Keep connect failures fast and cap total time so the API stays responsive.
    # Vocab generation is still allowed a bit longer to let local models respond.
    effective = min(float(settings.llm_timeout_seconds), 25.0)
    timeout = httpx.Timeout(effective, connect=min(2.0, effective))

    try:
        async with httpx.AsyncClient(base_url=settings.llm_base_url, timeout=timeout) as client:
            model = await _resolve_llm_model(client)

            async def _translate_example_to_zh(example_en: str) -> str:
                ex = (example_en or "").strip()
                if not ex:
                    return ""
                translate_prompt = (
                    "把下面这句英文例句翻译成中文。只输出中文翻译本身，不要输出任何多余内容。\n"
                    f"英文：{ex}"
                )
                payload: dict[str, Any] = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": translate_prompt},
                    ],
                    "temperature": 0.0,
                    "max_tokens": 160,
                }
                r = await client.post(
                    "/chat/completions",
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                    json=payload,
                )
                r.raise_for_status()
                txt = _extract_chat_response_text(r.json())
                return (txt or "").strip().strip('"')

            async def _request_vocab_json(user_prompt: str) -> str:
                base_payload: dict[str, Any] = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 700,
                }

                payload: dict[str, Any] = {**base_payload, "response_format": {"type": "json_object"}}
                r = await client.post(
                    "/chat/completions",
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                    json=payload,
                )
                try:
                    r.raise_for_status()
                except httpx.HTTPStatusError as e:
                    status = getattr(e.response, "status_code", None)
                    if status in (400, 404, 422):
                        r = await client.post(
                            "/chat/completions",
                            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                            json=base_payload,
                        )
                        r.raise_for_status()
                    else:
                        raise

                return _extract_chat_response_text(r.json())

            text = await _request_vocab_json(prompt)
            if text:
                parsed = _extract_vocab_from_text(text)
                defs = parsed.get("definitions")
                if isinstance(defs, list) and defs:
                    normalized_defs: list[dict[str, str]] = []
                    for d in defs:
                        if not isinstance(d, dict):
                            continue
                        meaning = str(d.get("meaning") or "").strip()
                        example = str(d.get("example") or "").strip()
                        example_translation = str(d.get("example_translation") or "").strip()

                        if example and not example_translation:
                            try:
                                example_translation = await _translate_example_to_zh(example)
                            except Exception:
                                example_translation = ""

                        if example and not example_translation:
                            example_translation = "暂无"

                        if meaning or example or example_translation:
                            normalized_defs.append(
                                {
                                    "meaning": meaning,
                                    "example": example,
                                    "example_translation": example_translation,
                                }
                            )

                    # If result looks incomplete for common/polysemous terms, retry once with an explicit expand prompt.
                    if len(normalized_defs) < 2 and _should_expand(t):
                        try:
                            t2 = await _request_vocab_json(expand_prompt)
                            if t2:
                                p2 = _extract_vocab_from_text(t2)
                                d2 = p2.get("definitions")
                                if isinstance(d2, list) and d2:
                                    for d in d2:
                                        if not isinstance(d, dict):
                                            continue
                                        m2 = str(d.get("meaning") or "").strip()
                                        e2 = str(d.get("example") or "").strip()
                                        z2 = str(d.get("example_translation") or "").strip()
                                        if e2 and not z2:
                                            try:
                                                z2 = await _translate_example_to_zh(e2)
                                            except Exception:
                                                z2 = ""
                                        if e2 and not z2:
                                            z2 = "暂无"
                                        if m2 or e2 or z2:
                                            normalized_defs.append(
                                                {
                                                    "meaning": m2,
                                                    "example": e2,
                                                    "example_translation": z2,
                                                }
                                            )
                        except Exception:
                            pass

                    # De-duplicate by meaning text.
                    deduped: list[dict[str, str]] = []
                    seen: set[str] = set()
                    for d in normalized_defs:
                        key = (d.get("meaning") or "").strip()
                        if not key:
                            continue
                        if key in seen:
                            continue
                        seen.add(key)
                        deduped.append(d)

                    if deduped:
                        # Keep legacy top-level keys for backward compatibility.
                        first = deduped[0]
                        return {
                            "meaning": first.get("meaning") or "",
                            "example": first.get("example") or "",
                            "example_translation": first.get("example_translation") or "",
                            "definitions": deduped,
                        }

                # Legacy single-definition shape.
                meaning = str(parsed.get("meaning") or "").strip()
                example = str(parsed.get("example") or "").strip()
                example_translation = str(parsed.get("example_translation") or "").strip()

                if example and (not example_translation or example_translation == "暂无"):
                    try:
                        example_translation = await _translate_example_to_zh(example)
                    except Exception:
                        example_translation = example_translation or ""

                if example and not example_translation:
                    example_translation = "暂无"

                return {
                    "meaning": meaning,
                    "example": example,
                    "example_translation": example_translation,
                    "definitions": [],
                }
    except Exception:
        return {
            "meaning": "暂无（LLM 未连接或超时）",
            "example": "暂无",
            "example_translation": "暂无",
            "definitions": [],
        }

    return {"meaning": "暂无（LLM 输出为空）", "example": "暂无", "example_translation": "暂无", "definitions": []}


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

    effective = min(float(settings.llm_timeout_seconds), 15.0)
    timeout = httpx.Timeout(effective, connect=min(2.0, effective))

    try:
        async with httpx.AsyncClient(base_url=settings.llm_base_url, timeout=timeout) as client:
            model = await _resolve_llm_model(client)
            payload: dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            }
            resp = await client.post(
                "/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            # OpenAI 兼容：choices[0].message.content
            text = _extract_chat_response_text(data)
            if text:
                return text
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

    effective = min(float(settings.llm_timeout_seconds), 15.0)
    timeout = httpx.Timeout(effective, connect=min(2.0, effective))

    try:
        async with httpx.AsyncClient(base_url=settings.llm_base_url, timeout=timeout) as client:
            model = await _resolve_llm_model(client)
            payload: dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": "system", "content": sp},
                    {"role": "user", "content": ut},
                ],
                "temperature": 0.4,
            }
            resp = await client.post(
                "/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            text = _extract_chat_response_text(data)
            if text:
                return text
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
    total = 60
    return {
        "score": total,
        "scores": {
            "vocabulary": total,
            "grammar": total,
            "fluency": total,
            "logic": total,
            "content": total,
            "structure": total,
            "total": total,
        },
        "feedback": "（降级）未连接到 LLM，返回最小可用批改结果。",
        "evaluation": "",
        "errors": [],
        "suggestions": ["检查拼写与标点", "尽量使用更具体的词汇"],
        "questions": [],
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

    evaluation = obj.get("evaluation")
    if not isinstance(evaluation, str):
        evaluation = ""

    errors = obj.get("errors")
    if not isinstance(errors, list):
        errors = []

    suggestions = obj.get("suggestions")
    if not isinstance(suggestions, list):
        suggestions = []
    suggestions = [s for s in suggestions if isinstance(s, str) and s.strip()]

    questions = obj.get("questions")
    if not isinstance(questions, list):
        questions = []
    questions = [q for q in questions if isinstance(q, str) and q.strip()]

    rewritten = obj.get("rewritten")
    if not isinstance(rewritten, str):
        rewritten = ocr_text.strip()

    scores_obj = obj.get("scores")
    if isinstance(scores_obj, dict):
        def _int_score(key: str) -> int:
            try:
                v = int(scores_obj.get(key, score))
            except Exception:
                v = score
            return max(0, min(100, v))

        scores = {
            "vocabulary": _int_score("vocabulary"),
            "grammar": _int_score("grammar"),
            "fluency": _int_score("fluency"),
            "logic": _int_score("logic"),
            "content": _int_score("content"),
            "structure": _int_score("structure"),
            "total": _int_score("total"),
        }
        score = scores.get("total", score)
    else:
        scores = {
            "vocabulary": score,
            "grammar": score,
            "fluency": score,
            "logic": score,
            "content": score,
            "structure": score,
            "total": score,
        }

    return {
        "score": score,
        "scores": scores,
        "feedback": feedback,
        "evaluation": evaluation,
        "errors": errors,
        "suggestions": suggestions,
        "questions": questions,
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
            payload["model"] = await _resolve_llm_model(client)
            resp = await client.post(
                "/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            content = _extract_chat_response_text(data)
            if isinstance(content, str) and content.strip():
                raw = content.strip()
                obj: Any | None = None
                try:
                    obj = json.loads(raw)
                except Exception:
                    json_text = _extract_json_object(raw)
                    if json_text:
                        try:
                            obj = json.loads(json_text)
                        except Exception:
                            obj = None

                # Double-decode if model returned a JSON string.
                if isinstance(obj, str):
                    try:
                        obj2 = json.loads(obj)
                        obj = obj2
                    except Exception:
                        pass

                if obj is not None:
                    return _normalize_essay_result(obj, ocr_text=ocr_text, language=language)
    except Exception:
        return _fallback_essay_result(ocr_text=ocr_text, language=language)

    return _fallback_essay_result(ocr_text=ocr_text, language=language)
