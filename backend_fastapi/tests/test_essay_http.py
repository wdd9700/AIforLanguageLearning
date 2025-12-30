from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import create_engine

from app.db import init_db, override_engine_for_tests
from app.main import app


def test_essay_grade_and_get_via_http(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    override_engine_for_tests(engine)
    init_db()

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
