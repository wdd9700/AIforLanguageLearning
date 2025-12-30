from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import create_engine

from app.db import init_db, override_engine_for_tests
from app.main import app


def test_v5_vocab_query_compat(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    override_engine_for_tests(engine)
    init_db()

    client = TestClient(app)
    resp = client.post("/api/query/vocabulary", json={"word": "hello"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["word"] == "hello"
    assert isinstance(data["definitions"], list)
    assert data["definitions"]


def test_v5_essay_correct_text_compat(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    override_engine_for_tests(engine)
    init_db()

    client = TestClient(app)
    resp = client.post("/api/essay/correct", json={"text": "I has a pen.", "language": "english"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert isinstance(data.get("original"), str)
    assert isinstance(data.get("correction"), str)
    assert isinstance(data.get("scores"), dict)
    assert isinstance(data.get("feedback"), str)


def test_v5_learning_stats_compat(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    override_engine_for_tests(engine)
    init_db()

    client = TestClient(app)
    resp = client.get("/api/learning/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert set(data.keys()) == {"vocabulary", "essay", "dialogue", "analysis"}


def test_v5_learning_analyze_compat(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    override_engine_for_tests(engine)
    init_db()

    client = TestClient(app)
    resp = client.post("/api/learning/analyze", json={"dimension": "vocabulary"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert data["dimension"] == "vocabulary"
    assert isinstance(data.get("visualization"), dict)
