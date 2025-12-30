from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_ws_echo() -> None:
    client = TestClient(app)
    with client.websocket_connect("/ws/v1?session_id=test&conversation_id=conv") as ws:
        first = ws.receive_json()
        assert first["type"] == "TASK_STARTED"

        ws.send_json({"hello": "world"})
        msg = ws.receive_json()
        assert msg["type"] == "ECHO"
        assert msg["payload"]["received"]["hello"] == "world"
