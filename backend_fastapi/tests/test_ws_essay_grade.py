from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import create_engine

from app.db import init_db, override_engine_for_tests
from app.main import app


def test_ws_grade_essay_emits_result(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    override_engine_for_tests(engine)
    init_db()

    client = TestClient(app)
    with client.websocket_connect("/ws/v1?session_id=test&conversation_id=conv_essay") as ws:
        first = ws.receive_json()
        assert first["type"] == "TASK_STARTED"

        ws.send_json(
            {
                "type": "GRADE_ESSAY",
                "request_id": "req1",
                "payload": {"language": "en", "ocr_text": "I has a pen."},
            }
        )

        types = []
        last = None
        for _ in range(10):
            last = ws.receive_json()
            types.append(last.get("type"))
            if last.get("type") == "TASK_FINISHED":
                break

        assert "TASK_STARTED" in types
        assert "ANALYSIS_RESULT" in types
        assert last is not None
        assert last.get("type") == "TASK_FINISHED"


def test_ws_essay_replay_after_disconnect(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    override_engine_for_tests(engine)
    init_db()

    client = TestClient(app)

    with client.websocket_connect("/ws/v1?session_id=test&conversation_id=conv_essay") as ws:
        first = ws.receive_json()
        assert first["type"] == "TASK_STARTED"

        ws.send_json(
            {
                "type": "GRADE_ESSAY",
                "request_id": "req_replay",
                "payload": {"language": "en", "ocr_text": "I like learn English."},
            }
        )

        last = first
        for _ in range(20):
            last = ws.receive_json()
            if last.get("type") == "TASK_FINISHED":
                break
        assert last.get("type") == "TASK_FINISHED"
        max_seq = int(last["seq"])

    with client.websocket_connect(
        f"/ws/v1?session_id=test&conversation_id=conv_essay&last_seq=0"
    ) as ws:
        replayed = []
        for _ in range(30):
            msg = ws.receive_json()
            replayed.append(msg.get("type"))
            if int(msg.get("seq", 0)) >= max_seq:
                break

        assert "TASK_STARTED" in replayed
        assert "ANALYSIS_RESULT" in replayed
        assert "TASK_FINISHED" in replayed
