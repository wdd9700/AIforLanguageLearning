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
    assert isinstance(data.get("appConfig"), dict)


def test_system_config_update_returns_success() -> None:
    client = TestClient(app)
    resp = client.post("/api/system/config", json={"llmEndpoint": "http://127.0.0.1:1234/v1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("success") is True


def test_system_config_update_normalizes_and_clamps() -> None:
    client = TestClient(app)

    resp = client.post(
        "/api/system/config",
        json={
            "llmEndpoint": "127.0.0.1:1234/v1/",
            "asr": {
                "backend": "invalid-backend",
                "vad": {
                    "mode": 99,
                    "silenceMs": 1,
                },
            },
        },
    )
    assert resp.status_code == 200
    assert resp.json().get("success") is True

    get_resp = client.get("/api/system/config")
    assert get_resp.status_code == 200
    data = get_resp.json()["data"]

    assert data["llmEndpoint"] == "http://127.0.0.1:1234/v1"
    assert int(data["asr"]["vad"]["mode"]) == 3
    assert int(data["asr"]["vad"]["silenceMs"]) == 200


def test_system_config_update_app_config_persisted() -> None:
    client = TestClient(app)

    resp = client.post(
        "/api/system/config",
        json={
            "appConfig": {
                "general": {"theme": "system", "language": "en-US", "autoUpdate": False},
                "audio": {"inputDevice": "mic1", "outputDevice": "spk1", "volume": 120},
                "ai": {"model": "local-model", "temperature": 5, "voice": "alloy"},
                "backend": {"url": "localhost:8011", "wsUrl": "ws://localhost:8011"},
            }
        },
    )
    assert resp.status_code == 200
    assert resp.json().get("success") is True

    data = client.get("/api/system/config").json()["data"]["appConfig"]
    assert data["general"]["theme"] == "system"
    assert data["general"]["language"] == "en-US"
    assert data["general"]["autoUpdate"] is False
    assert int(data["audio"]["volume"]) == 100
    assert float(data["ai"]["temperature"]) == 2.0
    assert data["backend"]["url"] == "http://localhost:8012"
    assert data["backend"]["wsUrl"] == "localhost:8012"
