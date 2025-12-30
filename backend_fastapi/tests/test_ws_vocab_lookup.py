from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine

from app.db import init_db, override_engine_for_tests
from app.main import app
from app.models import PublicVocabEntry


def test_ws_lookup_vocab_emits_result(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    override_engine_for_tests(engine)
    init_db()

    with Session(engine) as session:
        session.add(PublicVocabEntry(term="hello", definition="释义：你好\n例句：Hello!", lang="en"))
        session.commit()

    client = TestClient(app)
    with client.websocket_connect("/ws/v1?session_id=test&conversation_id=conv") as ws:
        first = ws.receive_json()
        assert first["type"] == "TASK_STARTED"

        ws.send_json({"type": "LOOKUP_VOCAB", "payload": {"term": "hello"}})

        types = []
        payloads = []
        for _ in range(5):
            msg = ws.receive_json()
            types.append(msg.get("type"))
            payloads.append(msg.get("payload"))
            if msg.get("type") == "TASK_FINISHED":
                break

        assert "VOCAB_RESULT" in types
        idx = types.index("VOCAB_RESULT")
        assert payloads[idx]["term"] == "hello"
        assert payloads[idx]["from_public_vocab"] is True


def test_ws_replay_after_disconnect(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    override_engine_for_tests(engine)
    init_db()

    with Session(engine) as session:
        session.add(PublicVocabEntry(term="hello", definition="释义：你好\n例句：Hello!", lang="en"))
        session.commit()

    client = TestClient(app)

    # 先产生一段事件流（会落库）
    with client.websocket_connect("/ws/v1?session_id=test&conversation_id=conv") as ws:
        first = ws.receive_json()
        assert first["type"] == "TASK_STARTED"

        ws.send_json({"type": "LOOKUP_VOCAB", "request_id": "req1", "payload": {"term": "hello"}})

        last = first
        for _ in range(10):
            last = ws.receive_json()
            if last.get("type") == "TASK_FINISHED":
                break
        assert last.get("type") == "TASK_FINISHED"
        max_seq = int(last["seq"])

    # 重连并请求回放：last_seq=0 应回放到最新（至少包含 TASK_STARTED/RESULT/FINISHED）
    with client.websocket_connect(
        f"/ws/v1?session_id=test&conversation_id=conv&last_seq=0"
    ) as ws:
        replayed_types = []
        for _ in range(10):
            msg = ws.receive_json()
            replayed_types.append(msg.get("type"))
            if int(msg.get("seq", 0)) >= max_seq:
                break

        assert "TASK_STARTED" in replayed_types
        assert "VOCAB_RESULT" in replayed_types
        assert "TASK_FINISHED" in replayed_types
