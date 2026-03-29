from __future__ import annotations

import base64
from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import create_engine

from app.db import init_db, override_engine_for_tests
from app.main import app


def test_essay_grade_and_get_via_http(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    override_engine_for_tests(engine)
    init_db()

    async def _fake_grade_essay(*, ocr_text: str, language: str):
        return {
            "score": 80,
            "feedback": "ok",
            "errors": [],
            "suggestions": ["improve grammar"],
            "rewritten": "I have a pen. I like learning English.",
            "scores": {
                "vocabulary": 80,
                "grammar": 80,
                "fluency": 80,
                "logic": 80,
                "content": 80,
                "structure": 80,
                "total": 80,
            },
        }

    monkeypatch.setattr("app.routers.essays.grade_essay", _fake_grade_essay)

    client = TestClient(app)

    resp = client.post(
        "/v1/essays/grade",
        json={
            "session_id": "test",
            "conversation_id": "conv_test",
            "request_id": "req1",
            "language": "en",
            "ocr_text": "I has a pen. I like learn English.",
        },
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["conversation_id"] == "conv_test"
    assert body["request_id"] == "req1"
    assert isinstance(body["submission_id"], int)

    assert isinstance(body["score"], int)
    assert 0 <= body["score"] <= 100

    result = body["result"]
    assert isinstance(result, dict)
    assert "score" in result
    assert "feedback" in result
    assert "errors" in result
    assert "suggestions" in result
    assert "rewritten" in result

    submission_id = body["submission_id"]

    resp2 = client.get(f"/v1/essays/{submission_id}")
    assert resp2.status_code == 200
    got = resp2.json()
    assert got["submission_id"] == submission_id
    assert got["conversation_id"] == "conv_test"
    assert got["request_id"] == "req1"
    assert got["language"] == "en"
    assert "I has a pen" in got["ocr_text"]
    assert isinstance(got["result"], dict)


def test_essay_grade_ocr_via_http(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    override_engine_for_tests(engine)
    init_db()

    monkeypatch.setattr("app.routers.essays.ocr_image_base64", lambda image, language="english": "I has a pen.")

    async def _fake_grade_essay(*, ocr_text: str, language: str):
        return {
            "score": 78,
            "feedback": "不错",
            "errors": ["grammar"],
            "suggestions": ["use have"],
            "rewritten": "I have a pen.",
            "scores": {
                "vocabulary": 78,
                "grammar": 76,
                "fluency": 79,
                "logic": 80,
                "content": 77,
                "structure": 78,
                "total": 78,
            },
        }

    monkeypatch.setattr("app.routers.essays.grade_essay", _fake_grade_essay)

    client = TestClient(app)
    payload = base64.b64encode(b"dummy").decode("utf-8")
    resp = client.post("/v1/essays/grade-ocr", json={"image": payload, "language": "english"})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["submission_id"], int)
    assert int(body["score"]) == 78
    assert isinstance(body["result"], dict)
