from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.main import app


def _integration_enabled() -> bool:
    return os.getenv("AIFL_RUN_INTEGRATION", "").strip() in {"1", "true", "True"}


@pytest.mark.integration
@pytest.mark.timeout(180)
def test_integration_llm_vocab_miss_generates_non_fallback() -> None:
    if not _integration_enabled():
        pytest.skip("integration tests disabled (set AIFL_RUN_INTEGRATION=1)")

    # 该测试严格走生产接口：不 seed DB，直接触发 LLM 生成
    with TestClient(app) as client:
        resp = client.post(
            "/v1/vocab/lookup",
            json={
                "term": "serendipity",
                "source": "manual",
                "session_id": "integration",
                "conversation_id": "conv_integration_llm",
            },
        )
    assert resp.status_code == 200
    body = resp.json()

    assert body["term"] == "serendipity"
    assert body["from_public_vocab"] is False

    definition = body.get("definition")
    assert isinstance(definition, str)
    assert len(definition.strip()) > 10

    # 必须不是降级文案（否则说明生产依赖不可用）
    assert "LLM 未连接" not in definition
    assert "超时" not in definition
