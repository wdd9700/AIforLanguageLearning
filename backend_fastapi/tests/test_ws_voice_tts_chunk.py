from __future__ import annotations

import base64
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import create_engine

from app.db import init_db, override_engine_for_tests
from app.main import app


def test_ws_voice_tts_chunk_order_and_last(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    override_engine_for_tests(engine)
    init_db()

    async def fake_stream_chat(*, system_prompt: str, user_text: str):
        yield "hi"

    def fake_tts(_text: str, *, sample_rate: int = 16000, channels: int = 1) -> bytes:
        # Force multi-chunk payload: 40KB
        return b"X" * (40 * 1024)

    monkeypatch.setattr("app.main.stream_chat", fake_stream_chat)
    monkeypatch.setattr("app.main.synthesize_tts_wav", lambda text: fake_tts(text))

    client = TestClient(app)
    with client.websocket_connect("/ws/v1?session_id=test&conversation_id=conv_voice_tts") as ws:
        _ = ws.receive_json()  # server TASK_STARTED

        ws.send_json(
            {
                "type": "AUDIO_START",
                "request_id": "voice1",
                "payload": {"sample_rate": 16000, "channels": 1, "encoding": "pcm_s16le"},
            }
        )
        _ = ws.receive_json()  # TASK_STARTED voice1

        dummy_pcm = b"\x00\x00" * 320
        ws.send_json(
            {
                "type": "AUDIO_CHUNK",
                "request_id": "voice1",
                "payload": {"data_b64": base64.b64encode(dummy_pcm).decode("utf-8")},
            }
        )
        ws.send_json({"type": "AUDIO_END", "request_id": "voice1"})

        seen = []
        for _ in range(80):
            m = ws.receive_json()
            seen.append(m)
            if m.get("type") == "TASK_FINISHED":
                break

        types = [m.get("type") for m in seen]
        assert "LLM_RESULT" in types
        assert "TTS_CHUNK" in types
        assert "TTS_RESULT" in types

        # Chunking order: all TTS_CHUNK after LLM_RESULT.
        first_llm = types.index("LLM_RESULT")
        first_tts = types.index("TTS_CHUNK")
        assert first_tts > first_llm

        chunks = [m for m in seen if m.get("type") == "TTS_CHUNK"]
        assert len(chunks) >= 2
        idxs = []
        for c in chunks:
            idx = (c.get("payload") or {}).get("index")
            assert idx is not None
            idxs.append(int(idx))
        assert idxs == list(range(len(chunks)))

        last = chunks[-1]
        assert bool((last.get("payload") or {}).get("is_last")) is True

        # Data should be valid base64.
        for c in chunks:
            b64 = (c.get("payload") or {}).get("data_b64")
            assert isinstance(b64, str)
            base64.b64decode(b64.encode("utf-8"))
