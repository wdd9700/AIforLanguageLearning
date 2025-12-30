from __future__ import annotations

import asyncio
import base64
import json
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, col, select

from .db import init_db
from .db import get_engine
from .llm import chat_complete, generate_definition, grade_essay, stream_chat, stream_definition
from .logging import configure_logging
from .models import ConversationEvent, EssayResult, EssaySubmission, PublicVocabEntry, UserVocabQuery
from .routers.auth import router as auth_router
from .routers.compat_v5 import router as compat_v5_router
from .routers.essays import router as essays_router
from .routers.system import router as system_router
from .routers.voice import router as voice_router
from .routers.vocab import router as vocab_router
from .settings import settings
from .tts import synthesize_tts_wav
from .voice_stream import (
    VoiceStream,
    VoiceStreamConfig,
    try_create_faster_whisper_transcriber,
    try_create_openai_whisper_transcriber,
)


configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 确保 sqlite 文件目录存在（默认 ./data/app.db）
    if settings.database_url.startswith("sqlite:///./"):
        db_rel = settings.database_url.removeprefix("sqlite:///./")
        db_dir = os.path.dirname(db_rel)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    init_db()
    yield


app = FastAPI(title="AIFL Backend (FastAPI)", lifespan=lifespan)

# Allow browser-based dev clients (Vite) and Electron renderer (Origin: null) to call the API.
# Without this, `npm run dev` will fail on CORS preflight for endpoints like `/api/voice/generate-prompt`.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:8011",
        "http://127.0.0.1:8011",
        "null",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vocab_router)
app.include_router(essays_router)
app.include_router(voice_router)
app.include_router(auth_router)
app.include_router(system_router)
app.include_router(compat_v5_router)


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "env": settings.app_env}


@app.websocket("/ws/v1")
async def ws_v1(ws: WebSocket) -> None:
    await ws.accept()

    session_id = ws.query_params.get("session_id") or "anonymous"
    conversation_id = ws.query_params.get("conversation_id") or f"conv_{uuid.uuid4().hex[:8]}"

    last_seq_raw = ws.query_params.get("last_seq")
    last_seq: int | None
    try:
        last_seq = int(last_seq_raw) if last_seq_raw is not None else None
    except ValueError:
        last_seq = None

    # seq 以 conversation_events 为准：全局（conversation_id 内）严格递增
    with Session(get_engine()) as session:
        max_seq = session.exec(
            select(ConversationEvent.seq)
            .where(ConversationEvent.conversation_id == conversation_id)
            .order_by(col(ConversationEvent.seq).desc())
        ).first()
    seq = int(max_seq or 0)

    async def send_event(
        event_type: str,
        payload: dict,
        *,
        request_id: str = "ws",
        final: bool = False,
        log: bool = True,
        ts: int = 0,
        force_seq: int | None = None,
    ) -> None:
        nonlocal seq

        if force_seq is not None:
            msg_seq = force_seq
        else:
            seq += 1
            msg_seq = seq

        msg: dict = {
            "type": event_type,
            "seq": msg_seq,
            "ts": ts,
            "session_id": session_id,
            "conversation_id": conversation_id,
            "request_id": request_id,
            "payload": payload,
        }
        if final:
            msg["final"] = True

        await ws.send_json(msg)

        if log:
            with Session(get_engine()) as session:
                session.add(
                    ConversationEvent(
                        session_id=session_id,
                        conversation_id=conversation_id,
                        seq=msg_seq,
                        type=event_type,
                        ts=ts,
                        request_id=request_id,
                        final=bool(final),
                        payload=payload,
                    )
                )
                session.commit()

    def get_latest_system_prompt() -> str:
        try:
            with Session(get_engine()) as session:
                evt = session.exec(
                    select(ConversationEvent)
                    .where(ConversationEvent.conversation_id == conversation_id)
                    .where(ConversationEvent.type == "CONTEXT_SET")
                    .order_by(col(ConversationEvent.seq).desc())
                ).first()
                if evt is None:
                    return ""
                payload = dict(evt.payload or {})
                sp = payload.get("system_prompt") or payload.get("systemPrompt")
                return str(sp or "")
        except Exception:
            return ""

    # 重连恢复：先重放遗漏事件，再继续处理后续消息
    if last_seq is not None:
        with Session(get_engine()) as session:
            rows = session.exec(
                select(ConversationEvent)
                .where(ConversationEvent.conversation_id == conversation_id)
                .where(ConversationEvent.seq > last_seq)
                .order_by(col(ConversationEvent.seq).asc())
            ).all()

        for row in rows:
            await send_event(
                row.type,
                dict(row.payload or {}),
                request_id=row.request_id,
                final=bool(row.final),
                log=False,
                ts=int(row.ts),
                force_seq=int(row.seq),
            )
    else:
        await send_event("TASK_STARTED", {"message": "connected"})

    try:
        voice_streams: dict[str, VoiceStream] = {}
        voice_last_activity_ms: dict[str, int] = {}
        voice_partial_tasks: dict[str, asyncio.Task[None]] = {}
        voice_asr_only: dict[str, bool] = {}
        voice_finalize_tasks: dict[str, asyncio.Task[None]] = {}
        voice_completed: set[str] = set()
        voice_aborted: set[str] = set()

        pending_binary_chunk_for: str | None = None
        asr_transcriber = None
        if settings.enable_asr:
            if settings.asr_backend == "faster-whisper":
                asr_transcriber = try_create_faster_whisper_transcriber(
                    model_name=settings.asr_model,
                    device=settings.asr_device,
                    compute_type=settings.asr_compute_type,
                )
            elif settings.asr_backend == "openai-whisper":
                asr_transcriber = try_create_openai_whisper_transcriber(
                    model_name=settings.asr_model,
                    device=settings.asr_device,
                )

        async def abort_voice_request(req_id: str, *, reason: str) -> None:
            # Idempotent: abort only once.
            if req_id in voice_completed:
                return

            voice_aborted.add(req_id)

            # Cancel in-flight tasks (partial/finalize).
            t = voice_partial_tasks.pop(req_id, None)
            if t is not None and not t.done():
                t.cancel()

            ft = voice_finalize_tasks.pop(req_id, None)
            if ft is not None and not ft.done():
                ft.cancel()

            # Drop buffers/state.
            voice_streams.pop(req_id, None)
            voice_last_activity_ms.pop(req_id, None)
            voice_asr_only.pop(req_id, None)

            await send_event(
                "TASK_ABORTED",
                {"reason": reason},
                request_id=req_id,
            )
            await send_event(
                "TASK_FINISHED",
                {"ok": False, "reason": reason},
                request_id=req_id,
                final=True,
            )
            voice_completed.add(req_id)

        async def cleanup_stale_voice_requests() -> None:
            now_ms = int(time.time() * 1000)
            idle_ms = int(settings.voice_request_idle_seconds) * 1000
            if idle_ms <= 0 or not voice_last_activity_ms:
                return

            stale_ids = [
                rid
                for rid, last_ms in voice_last_activity_ms.items()
                if now_ms - int(last_ms) > idle_ms
            ]
            for rid in stale_ids:
                voice_last_activity_ms.pop(rid, None)
                voice_streams.pop(rid, None)
                voice_asr_only.pop(rid, None)
                t = voice_partial_tasks.pop(rid, None)
                if t is not None and not t.done():
                    t.cancel()
                ft = voice_finalize_tasks.pop(rid, None)
                if ft is not None and not ft.done():
                    ft.cancel()
                await send_event(
                    "ERROR",
                    {"code": "TIMEOUT", "message": "voice request idle timeout"},
                    request_id=rid,
                )
                await send_event(
                    "TASK_FINISHED",
                    {"ok": False, "reason": "timeout"},
                    request_id=rid,
                    final=True,
                )

        async def finalize_voice_request(req_id: str, *, reason: str) -> None:
            # Idempotent: only finalize once.
            if req_id in voice_completed:
                return

            if req_id in voice_aborted:
                return

            stream = voice_streams.pop(req_id, None)
            voice_last_activity_ms.pop(req_id, None)
            asr_only = bool(voice_asr_only.pop(req_id, False))
            if stream is None:
                return

            # Wait/stop any in-flight partial.
            t = voice_partial_tasks.pop(req_id, None)
            if t is not None and not t.done():
                try:
                    await asyncio.wait_for(t, timeout=15.0)
                except asyncio.TimeoutError:
                    t.cancel()

            final_text = await stream.transcribe_final()
            await send_event("ASR_FINAL", {"text": final_text, "reason": reason}, request_id=req_id)

            if req_id in voice_aborted:
                return

            if asr_only:
                await send_event(
                    "TASK_FINISHED",
                    {"ok": True, "asr_only": True, "reason": reason},
                    request_id=req_id,
                    final=True,
                )
                voice_completed.add(req_id)
                voice_finalize_tasks.pop(req_id, None)
                return

            user_prompt = (final_text or "").strip()
            if not user_prompt:
                reply_md = "（未检测到语音内容）"
            else:
                system_prompt = get_latest_system_prompt()
                parts: list[str] = []
                streamed = False
                async for delta in stream_chat(system_prompt=system_prompt, user_text=user_prompt):
                    if req_id in voice_aborted:
                        return
                    streamed = True
                    parts.append(delta)
                    await send_event(
                        "LLM_TOKEN",
                        {"text": delta},
                        request_id=req_id,
                    )
                if streamed:
                    reply_md = ("".join(parts)).strip() or "（LLM 输出为空）"
                else:
                    reply_md = await chat_complete(system_prompt=system_prompt, user_text=user_prompt)

            if req_id in voice_aborted:
                return

            await send_event(
                "LLM_RESULT",
                {"format": "markdown", "markdown": reply_md},
                request_id=req_id,
            )

            if req_id in voice_aborted:
                return

            # P1: TTS_CHUNK
            wav_bytes = await asyncio.to_thread(synthesize_tts_wav, reply_md)
            chunk_size = int(settings.tts_chunk_size_bytes) if int(settings.tts_chunk_size_bytes) > 0 else 16 * 1024
            chunks = [wav_bytes[i : i + chunk_size] for i in range(0, len(wav_bytes), chunk_size)] or [b""]

            for idx, ch in enumerate(chunks):
                if req_id in voice_aborted:
                    return
                await send_event(
                    "TTS_CHUNK",
                    {
                        "format": "wav",
                        "sample_rate": 16000,
                        "channels": 1,
                        "data_b64": base64.b64encode(ch).decode("utf-8"),
                        "index": idx,
                        "is_last": idx == (len(chunks) - 1),
                    },
                    request_id=req_id,
                )

            # Backward-compatible: still provide the full audio in one event.
            await send_event(
                "TTS_RESULT",
                {"text": reply_md, "audio_base64": base64.b64encode(wav_bytes).decode("utf-8")},
                request_id=req_id,
            )
            await send_event("TASK_FINISHED", {"ok": True, "reason": reason}, request_id=req_id, final=True)
            voice_completed.add(req_id)
            voice_finalize_tasks.pop(req_id, None)

        while True:
            await cleanup_stale_voice_requests()

            poll_timeout_s: float | None = (
                1.0 if int(settings.voice_request_idle_seconds) > 0 else None
            )
            try:
                if poll_timeout_s is None:
                    raw = await ws.receive()
                else:
                    raw = await asyncio.wait_for(ws.receive(), timeout=poll_timeout_s)
            except asyncio.TimeoutError:
                continue

            if isinstance(raw, dict) and raw.get("type") == "websocket.disconnect":
                break

            # Starlette websocket message shape: {'type': 'websocket.receive', 'text': str|None, 'bytes': bytes|None}
            data: dict | None = None
            if isinstance(raw, dict) and raw.get("type") == "websocket.receive":
                b = raw.get("bytes")
                t = raw.get("text")

                if b is not None:
                    rid = pending_binary_chunk_for
                    pending_binary_chunk_for = None
                    if rid is None:
                        await send_event(
                            "ERROR",
                            {
                                "code": "VALIDATION_ERROR",
                                "message": "unexpected binary frame (send AUDIO_CHUNK_BIN first)",
                            },
                            request_id="ws",
                        )
                        continue

                    if rid in voice_completed or rid in voice_aborted:
                        continue

                    stream = voice_streams.get(rid)
                    if stream is None:
                        await send_event(
                            "ERROR",
                            {
                                "code": "VALIDATION_ERROR",
                                "message": "unknown request_id (call AUDIO_START first)",
                            },
                            request_id=rid,
                        )
                        continue

                    size = await stream.add_chunk_bytes(b)
                    voice_last_activity_ms[rid] = int(time.time() * 1000)

                    existing = voice_partial_tasks.get(rid)
                    if existing is None or existing.done():

                        async def _run_partial_bin(rid2: str, buffer_size: int) -> None:
                            s = voice_streams.get(rid2)
                            if s is None:
                                return
                            try:
                                partial = await s.maybe_transcribe_partial()
                                if partial:
                                    await send_event(
                                        "ASR_PARTIAL",
                                        {"text": partial, "bytes": buffer_size},
                                        request_id=rid2,
                                    )
                            except Exception as e:
                                await send_event(
                                    "ERROR",
                                    {"code": "ASR_ERROR", "message": str(e)},
                                    request_id=rid2,
                                )

                        voice_partial_tasks[rid] = asyncio.create_task(_run_partial_bin(rid, size))

                    if stream.vad_should_finalize():
                        fin = voice_finalize_tasks.get(rid)
                        if fin is None or fin.done():
                            tsk = voice_partial_tasks.pop(rid, None)
                            if tsk is not None and not tsk.done():
                                tsk.cancel()

                            async def _run_finalize_bin(rid2: str) -> None:
                                try:
                                    await finalize_voice_request(rid2, reason="vad")
                                except Exception as e:
                                    await send_event(
                                        "ERROR",
                                        {"code": "ASR_ERROR", "message": str(e)},
                                        request_id=rid2,
                                    )

                            voice_finalize_tasks[rid] = asyncio.create_task(_run_finalize_bin(rid))
                    continue

                if isinstance(t, str) and t:
                    try:
                        obj = json.loads(t)
                        if isinstance(obj, dict):
                            data = obj
                    except Exception:
                        data = None

            if data is None:
                await send_event(
                    "ERROR",
                    {"code": "VALIDATION_ERROR", "message": "invalid websocket message"},
                    request_id="ws",
                )
                continue

            msg_type = data.get("type") if isinstance(data, dict) else None
            payload = data.get("payload") if isinstance(data, dict) else None

            # Set/update conversation context (system prompt) for voice dialogue.
            if msg_type == "CONTEXT_SET" and isinstance(payload, dict):
                req_id = str(data.get("request_id") or f"ctx_{uuid.uuid4().hex[:8]}")
                ts = int(time.time() * 1000)
                system_prompt = str(payload.get("system_prompt") or payload.get("systemPrompt") or "")
                language = str(payload.get("language") or "")
                await send_event(
                    "CONTEXT_SET",
                    {"system_prompt": system_prompt, "language": language},
                    request_id=req_id,
                    ts=ts,
                    final=False,
                    log=True,
                )
                continue

            # -----------------
            # 语音对话（P0）：前端切片上传音频，后端流式 ASR + 最终 LLM + TTS
            # 客户端消息：
            # - AUDIO_START: {request_id, payload:{sample_rate,channels,encoding}}
            # - AUDIO_CHUNK: {request_id, payload:{data_b64}}
            # - AUDIO_END:   {request_id}
            # 服务端事件：ASR_PARTIAL/ASR_FINAL/LLM_TOKEN/LLM_RESULT/TTS_CHUNK/TTS_RESULT + TASK_FINISHED
            # -----------------
            if msg_type == "AUDIO_START" and isinstance(payload, dict):
                req_id = str(data.get("request_id") or f"req_{uuid.uuid4().hex[:10]}")

                # Barge-in (P1): starting a new utterance aborts any in-flight agent output.
                inflight = [
                    rid
                    for rid, t in list(voice_finalize_tasks.items())
                    if rid != req_id and t is not None and not t.done() and rid not in voice_completed
                ]
                for rid in inflight:
                    await abort_voice_request(rid, reason="barge_in")

                cfg = VoiceStreamConfig(
                    sample_rate=int(payload.get("sample_rate") or 16000),
                    channels=int(payload.get("channels") or 1),
                    encoding=str(payload.get("encoding") or "pcm_s16le"),
                    language=(str(payload.get("language")).strip() or None)
                    if payload.get("language") is not None
                    else None,
                    vad_enabled=bool(payload.get("vad_enabled") or settings.enable_vad),
                    vad_mode=int(payload.get("vad_mode") or settings.vad_mode),
                    vad_silence_ms=int(payload.get("vad_silence_ms") or settings.vad_silence_ms),
                )
                voice_streams[req_id] = VoiceStream(config=cfg, transcriber=asr_transcriber)
                voice_last_activity_ms[req_id] = int(time.time() * 1000)
                voice_asr_only[req_id] = bool(payload.get("asr_only") or False)
                await send_event(
                    "TASK_STARTED",
                    {"task": "voice_audio", "request_id": req_id, "config": cfg.__dict__},
                    request_id=req_id,
                )
                continue

            if msg_type == "AUDIO_CHUNK" and isinstance(payload, dict):
                req_id = str(data.get("request_id") or "")

                # 若该 request 已完成（VAD/客户端 end），后续 chunk 可能是网络/缓冲尾部：静默忽略。
                if req_id in voice_completed:
                    continue

                stream = voice_streams.get(req_id)
                if stream is None:
                    await send_event(
                        "ERROR",
                        {"code": "VALIDATION_ERROR", "message": "unknown request_id (call AUDIO_START first)"},
                        request_id=req_id or "ws",
                    )
                    continue

                data_b64 = str(payload.get("data_b64") or "")
                size = await stream.add_chunk_b64(data_b64)
                voice_last_activity_ms[req_id] = int(time.time() * 1000)

                # 真实时间流式输入时，不能在这里 await 重型 ASR（会导致 backpressure，客户端 send 卡死）。
                # 改为后台任务：每个 request_id 最多一个进行中的 partial 转写。
                existing = voice_partial_tasks.get(req_id)
                if existing is None or existing.done():

                    async def _run_partial(rid: str, buffer_size: int) -> None:
                        s = voice_streams.get(rid)
                        if s is None:
                            return
                        try:
                            partial = await s.maybe_transcribe_partial()
                            if partial:
                                await send_event(
                                    "ASR_PARTIAL",
                                    {"text": partial, "bytes": buffer_size},
                                    request_id=rid,
                                )
                        except Exception as e:
                            await send_event(
                                "ERROR",
                                {"code": "ASR_ERROR", "message": str(e)},
                                request_id=rid,
                            )

                    voice_partial_tasks[req_id] = asyncio.create_task(_run_partial(req_id, size))

                # VAD 自动收句：检测到持续静音后，后台 finalize（无需客户端发 AUDIO_END）。
                if stream.vad_should_finalize():
                    fin = voice_finalize_tasks.get(req_id)
                    if fin is None or fin.done():

                        # 尽量取消未完成的 partial，避免和 finalize 竞争模型。
                        t = voice_partial_tasks.pop(req_id, None)
                        if t is not None and not t.done():
                            t.cancel()

                        async def _run_finalize(rid: str) -> None:
                            try:
                                await finalize_voice_request(rid, reason="vad")
                            except Exception as e:
                                await send_event(
                                    "ERROR",
                                    {"code": "ASR_ERROR", "message": str(e)},
                                    request_id=rid,
                                )

                        voice_finalize_tasks[req_id] = asyncio.create_task(_run_finalize(req_id))
                continue

            # Binary audio chunk mode: client sends a JSON header then the next WS binary frame.
            # Client message:
            # - AUDIO_CHUNK_BIN: {request_id, payload:{}} followed by a binary frame with raw bytes.
            if msg_type == "AUDIO_CHUNK_BIN":
                req_id = str(data.get("request_id") or "")
                if not req_id:
                    await send_event(
                        "ERROR",
                        {"code": "VALIDATION_ERROR", "message": "missing request_id"},
                        request_id="ws",
                    )
                    continue
                pending_binary_chunk_for = req_id
                continue

            if msg_type == "AUDIO_END":
                req_id = str(data.get("request_id") or "")
                # 如果已被 VAD 自动 finalize，客户端再发 AUDIO_END 视为幂等重复：忽略。
                if req_id in voice_completed:
                    continue

                if req_id in voice_aborted:
                    continue

                stream = voice_streams.get(req_id)
                if stream is None:
                    await send_event(
                        "ERROR",
                        {"code": "VALIDATION_ERROR", "message": "unknown request_id (call AUDIO_START first)"},
                        request_id=req_id or "ws",
                    )
                    await send_event("TASK_FINISHED", {"ok": False}, request_id=req_id or "ws", final=True)
                    continue

                fin = voice_finalize_tasks.get(req_id)
                if fin is None or fin.done():

                    # 尽量取消未完成的 partial，避免和 finalize 竞争模型。
                    t = voice_partial_tasks.pop(req_id, None)
                    if t is not None and not t.done():
                        t.cancel()

                    async def _run_finalize(rid: str) -> None:
                        try:
                            await finalize_voice_request(rid, reason="client_end")
                        except asyncio.CancelledError:
                            raise
                        except Exception as e:
                            await send_event(
                                "ERROR",
                                {"code": "ASR_ERROR", "message": str(e)},
                                request_id=rid,
                            )

                    voice_finalize_tasks[req_id] = asyncio.create_task(_run_finalize(req_id))
                continue

            if msg_type == "LOOKUP_VOCAB" and isinstance(payload, dict):
                term = str(payload.get("term") or "").strip()
                req_id = str(data.get("request_id") or "ws") if isinstance(data, dict) else "ws"
                await send_event("VOCAB_LOOKUP_STARTED", {"term": term}, request_id=req_id)

                if not term:
                    await send_event("ERROR", {"code": "invalid_request", "message": "term is empty"})
                    await send_event("TASK_FINISHED", {"ok": False}, request_id=req_id, final=True)
                    continue

                with Session(get_engine()) as session:
                    entry = session.exec(
                        select(PublicVocabEntry).where(PublicVocabEntry.term == term)
                    ).first()

                    if entry is not None and entry.definition:
                        definition = entry.definition
                        from_public_vocab = True
                    else:
                        definition = await generate_definition(term)
                        from_public_vocab = False

                    session.add(
                        UserVocabQuery(
                            session_id=session_id,
                            conversation_id=conversation_id,
                            term=term,
                            source="manual",
                            result=definition,
                        )
                    )
                    session.commit()

                await send_event(
                    "VOCAB_RESULT",
                    {"term": term, "definition": definition, "from_public_vocab": from_public_vocab},
                    request_id=req_id,
                )

                await send_event("TASK_FINISHED", {"ok": True}, request_id=req_id, final=True)
                continue

            if msg_type == "GRADE_ESSAY" and isinstance(payload, dict):
                ocr_text = str(payload.get("ocr_text") or "").strip()
                language = str(payload.get("language") or "en").strip() or "en"
                req_id = str(data.get("request_id") or f"req_{uuid.uuid4().hex[:10]}")

                if not ocr_text:
                    await send_event(
                        "ERROR",
                        {"code": "invalid_request", "message": "ocr_text is empty"},
                        request_id=req_id,
                    )
                    await send_event("TASK_FINISHED", {"ok": False}, request_id=req_id, final=True)
                    continue

                # 先持久化 submission，确保事件里可以带 submission_id
                with Session(get_engine()) as session:
                    submission = EssaySubmission(
                        session_id=session_id,
                        conversation_id=conversation_id,
                        request_id=req_id,
                        ocr_text=ocr_text,
                        language=language,
                    )
                    session.add(submission)
                    session.commit()
                    session.refresh(submission)

                submission_id = submission.id
                if submission_id is None:
                    await send_event(
                        "ERROR",
                        {"code": "internal_error", "message": "failed to create submission"},
                        request_id=req_id,
                    )
                    await send_event("TASK_FINISHED", {"ok": False}, request_id=req_id, final=True)
                    continue

                await send_event(
                    "TASK_STARTED",
                    {"task": "essay_grade", "submission_id": submission_id, "language": language},
                    request_id=req_id,
                )

                result = await grade_essay(ocr_text=ocr_text, language=language)
                score = int(result.get("score") or 0)

                with Session(get_engine()) as session:
                    session.add(
                        EssayResult(
                            submission_id=int(submission_id),
                            score=score,
                            result=result,
                        )
                    )
                    session.commit()

                await send_event(
                    "ANALYSIS_RESULT",
                    {
                        "kind": "essay_grade",
                        "submission_id": submission_id,
                        "score": score,
                        "result": result,
                    },
                    request_id=req_id,
                )
                await send_event(
                    "TASK_FINISHED",
                    {"ok": True, "submission_id": submission_id},
                    request_id=req_id,
                    final=True,
                )
                continue

            # 默认：回显，证明链路可用
            await send_event("ECHO", {"received": data})
    except WebSocketDisconnect:
        return
