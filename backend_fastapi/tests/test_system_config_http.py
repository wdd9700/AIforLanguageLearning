from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_system_config_get_shape() -> None:
    client = TestClient(app)
    resp = client.get("/api/system/config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    data = body["data"]
    assert isinstance(data.get("port"), int)
    assert isinstance(data.get("llmEndpoint"), str)
    assert isinstance(data.get("models"), dict)
    assert isinstance(data.get("tts"), dict)
    assert isinstance(data.get("asr"), dict)


def test_system_config_update_returns_success() -> None:
    client = TestClient(app)
    resp = client.post("/api/system/config", json={"llmEndpoint": "http://127.0.0.1:1234/v1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("success") is True
