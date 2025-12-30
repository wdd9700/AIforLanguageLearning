from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import create_engine

from app.db import init_db, override_engine_for_tests
from app.main import app


def test_voice_generate_prompt_http(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    override_engine_for_tests(engine)
    init_db()

    client = TestClient(app)
    resp = client.post(
        "/api/voice/generate-prompt",
        json={"scenario": "ordering coffee", "language": "English"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body.get("systemPrompt"), str)
    assert "ordering coffee" in body["systemPrompt"]


def test_voice_start_session_http(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    override_engine_for_tests(engine)
    init_db()

    client = TestClient(app)
    resp = client.post(
        "/api/voice/start",
        json={"systemPrompt": "You are a helpful assistant."},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body.get("openingText"), str)
    assert body["openingText"].strip()
    assert "openingAudio" in body
    assert isinstance(body.get("openingAudio"), str)
