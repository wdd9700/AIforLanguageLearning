from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_auth_login_admin_ok() -> None:
    client = TestClient(app)
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body.get("data"), dict)
    data = body["data"]
    assert isinstance(data.get("accessToken"), str)
    assert data.get("accessToken")
    assert isinstance(data.get("user"), dict)
    assert data["user"]["username"] == "admin"


def test_auth_login_rejects_wrong_password() -> None:
    client = TestClient(app)
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert isinstance(body.get("error"), str)
