from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import create_engine

from app.db import init_db, override_engine_for_tests
from app.main import app


def test_learning_stats_http_shape(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    override_engine_for_tests(engine)
    init_db()

    client = TestClient(app)
    resp = client.get("/v1/learning/stats")
    assert resp.status_code == 200
    data = resp.json()

    assert isinstance(data.get("vocabulary"), int)
    assert isinstance(data.get("essay"), int)
    assert isinstance(data.get("dialogue"), int)
    assert isinstance(data.get("analysis"), int)


def test_learning_analyze_http_shape(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    override_engine_for_tests(engine)
    init_db()

    client = TestClient(app)
    resp = client.post("/v1/learning/analyze", json={"dimension": "vocabulary"})
    assert resp.status_code == 200
    data = resp.json()

    assert data.get("dimension") == "vocabulary"
    assert isinstance(data.get("score"), int)
    assert isinstance(data.get("trend"), int)
    assert isinstance(data.get("insights"), list)
    assert isinstance(data.get("recommendations"), list)
    assert isinstance(data.get("visualization"), dict)
