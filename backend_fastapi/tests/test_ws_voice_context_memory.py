from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import create_engine

from app.db import init_db, override_engine_for_tests
from app.main import app


def _run_voice_round(ws: Any, request_id: str, pcm_b64: str) -> list[dict[str, Any]]:
    ws.send_json(
        {
            "type": "AUDIO_START",
            "request_id": request_id,
            "payload": {"sample_rate": 16000, "channels": 1, "encoding": "pcm_s16le"},
        }
    )

    started = ws.receive_json()
    assert started["type"] == "TASK_STARTED"
    assert started["request_id"] == request_id

    ws.send_json({"type": "AUDIO_CHUNK", "request_id": request_id, "payload": {"data_b64": pcm_b64}})
    ws.send_json({"type": "AUDIO_END", "request_id": request_id})

    events: list[dict[str, Any]] = []
    for _ in range(30):
        msg = ws.receive_json()
        events.append(msg)
        if msg.get("type") == "TASK_FINISHED" and msg.get("request_id") == request_id:
            break

    return events


def test_ws_context_patch_persists_and_injects_history(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    override_engine_for_tests(engine)
    init_db()

    llm_calls: list[dict[str, Any]] = []

    async def fake_stream_chat(*, system_prompt: str, user_text: str, history=None):
        llm_calls.append(
            {
                "system_prompt": system_prompt,
                "user_text": user_text,
                "history": list(history or []),
            }
        )
        yield "stub-reply"

    monkeypatch.setattr("app.main.stream_chat", fake_stream_chat)

    client = TestClient(app)
    with client.websocket_connect("/ws/v1?session_id=test&conversation_id=conv_ctx") as ws:
        _ = ws.receive_json()  # server TASK_STARTED

        dummy_pcm = b"\x00\x00" * 320
        b64 = base64.b64encode(dummy_pcm).decode("utf-8")

        round1 = _run_voice_round(ws, "voice1", b64)
        assert any(m.get("type") == "LLM_RESULT" and m.get("request_id") == "voice1" for m in round1)

        ws.send_json(
            {
                "type": "CONTEXT_PATCH",
                "request_id": "ctx1",
                "payload": {"op": "replace", "text": "记住：用户喜欢简短回答"},
            }
        )
        patch_evt = ws.receive_json()
        assert patch_evt["type"] == "CONTEXT_MEMORY"
        patched_evt = ws.receive_json()
        assert patched_evt["type"] == "CONTEXT_PATCHED"
        assert patched_evt["request_id"] == "ctx1"
        assert (patched_evt.get("payload") or {}).get("memory") == "记住：用户喜欢简短回答"

        round2 = _run_voice_round(ws, "voice2", b64)
        assert any(m.get("type") == "LLM_RESULT" and m.get("request_id") == "voice2" for m in round2)

    assert len(llm_calls) >= 2
    second_call = llm_calls[-1]
    assert "记住：用户喜欢简短回答" in str(second_call.get("system_prompt") or "")

    history = second_call.get("history") or []
    assert any(h.get("role") == "assistant" for h in history)
    assert any(h.get("role") == "user" for h in history)
