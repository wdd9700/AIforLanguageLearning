from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_cors_preflight_allows_vite_dev_origin() -> None:
    origin = "http://localhost:5173"
    with TestClient(app) as client:
        resp = client.options(
            "/api/voice/generate-prompt",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,authorization",
            },
        )

    assert resp.status_code in (200, 204)
    assert resp.headers.get("access-control-allow-origin") == origin
