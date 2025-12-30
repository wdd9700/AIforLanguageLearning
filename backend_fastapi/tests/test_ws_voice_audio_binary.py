from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import create_engine

from app.db import init_db, override_engine_for_tests
from app.main import app


def test_ws_voice_audio_binary_chunk_min_flow(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    override_engine_for_tests(engine)
    init_db()

    client = TestClient(app)
    with client.websocket_connect("/ws/v1?session_id=test&conversation_id=conv_voice_bin") as ws:
        _ = ws.receive_json()  # server TASK_STARTED

        ws.send_json(
            {
                "type": "AUDIO_START",
                "request_id": "voice1",
                "payload": {"sample_rate": 16000, "channels": 1, "encoding": "pcm_s16le"},
            }
        )

        msg = ws.receive_json()
        assert msg["type"] == "TASK_STARTED"
        assert msg["request_id"] == "voice1"

        # Send header then a binary frame
        ws.send_json({"type": "AUDIO_CHUNK_BIN", "request_id": "voice1", "payload": {}})
        dummy_pcm = b"\x00\x00" * 320  # 20ms silence at 16kHz mono s16le
        ws.send_bytes(dummy_pcm)

        ws.send_json({"type": "AUDIO_END", "request_id": "voice1"})

        types = []
        for _ in range(25):
            m = ws.receive_json()
            types.append(m.get("type"))
            if m.get("type") == "TASK_FINISHED":
                break

        assert "ASR_FINAL" in types
        assert "LLM_RESULT" in types
        assert "TTS_CHUNK" in types
        assert "TTS_RESULT" in types
        assert "TASK_FINISHED" in types
