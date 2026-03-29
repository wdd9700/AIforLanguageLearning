from __future__ import annotations

import base64
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine

from app.db import init_db, override_engine_for_tests
from app.main import app
from app.models import PublicVocabEntry


def test_vocab_lookup_http_uses_public_vocab(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    override_engine_for_tests(engine)
    init_db()

    with Session(engine) as session:
        session.add(PublicVocabEntry(term="hello", definition="释义：你好\n例句：Hello!", lang="en"))
        session.commit()

    client = TestClient(app)
    resp = client.post("/v1/vocab/lookup", json={"term": "hello", "source": "manual"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["term"] == "hello"
    assert body["from_public_vocab"] is True
    assert "释义" in body["definition"]


def test_vocab_lookup_ocr_http(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    override_engine_for_tests(engine)
    init_db()

    monkeypatch.setattr("app.routers.vocab.ocr_image_base64", lambda image, language="english": "hello")
    async def _fake_generate_vocab_fields(_term: str):
        return {
            "meaning": "你好",
            "example": "Hello, world.",
            "example_translation": "你好，世界。",
        }

    monkeypatch.setattr("app.routers.vocab.generate_vocab_fields", _fake_generate_vocab_fields)

    client = TestClient(app)
    payload = base64.b64encode(b"dummy").decode("utf-8")
    resp = client.post("/v1/vocab/lookup-ocr", json={"image": payload, "language": "english"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["term"] == "hello"
    assert body["meaning"] == "你好"
