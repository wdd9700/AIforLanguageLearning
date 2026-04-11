"""模型路由故障切换测试"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.model_router import (
    ModelEndpoint,
    ModelProvider,
    ModelRouter,
    RoutingDecision,
    SceneType,
)


class TestModelRouterFallback:
    """模型路由器故障切换测试"""

    @pytest.mark.asyncio
    async def test_primary_failure_fallback_to_secondary(self) -> None:
        router = ModelRouter()
        decision = RoutingDecision(
            scene=SceneType.CHAT,
            primary_endpoint=ModelEndpoint(
                provider=ModelProvider.LOCAL,
                base_url="http://fail-1",
                api_key="key1",
                model_id="model1",
            ),
            fallback_endpoints=[
                ModelEndpoint(
                    provider=ModelProvider.LOCAL,
                    base_url="http://success-2",
                    api_key="key2",
                    model_id="model2",
                ),
            ],
            use_streaming=True,
            temperature=0.7,
        )

        async def mock_call(endpoint, messages, stream, temperature):
            if endpoint.base_url == "http://fail-1":
                raise ConnectionError("primary down")
            yield "fallback"

        with patch.object(router, "_call_endpoint", side_effect=mock_call):
            chunks = [c async for c in router.call_with_fallback(decision, messages=[], stream=True)]
            assert chunks == ["fallback"]

    @pytest.mark.asyncio
    async def test_all_endpoints_fail(self) -> None:
        router = ModelRouter()
        decision = RoutingDecision(
            scene=SceneType.CHAT,
            primary_endpoint=ModelEndpoint(
                provider=ModelProvider.LOCAL,
                base_url="http://fail-1",
                api_key="key1",
                model_id="model1",
            ),
            fallback_endpoints=[
                ModelEndpoint(
                    provider=ModelProvider.LOCAL,
                    base_url="http://fail-2",
                    api_key="key2",
                    model_id="model2",
                ),
            ],
            use_streaming=True,
            temperature=0.7,
        )

        async def mock_call(endpoint, messages, stream, temperature):
            raise ConnectionError("all down")

        with patch.object(router, "_call_endpoint", side_effect=mock_call):
            with pytest.raises(RuntimeError, match="All model endpoints failed"):
                _ = [c async for c in router.call_with_fallback(decision, messages=[], stream=True)]

    @pytest.mark.asyncio
    async def test_primary_success_no_fallback(self) -> None:
        router = ModelRouter()
        decision = RoutingDecision(
            scene=SceneType.CHAT,
            primary_endpoint=ModelEndpoint(
                provider=ModelProvider.LOCAL,
                base_url="http://success-1",
                api_key="key1",
                model_id="model1",
            ),
            fallback_endpoints=[],
            use_streaming=True,
            temperature=0.7,
        )

        async def mock_call(endpoint, messages, stream, temperature):
            yield "primary"

        with patch.object(router, "_call_endpoint", side_effect=mock_call):
            chunks = [c async for c in router.call_with_fallback(decision, messages=[], stream=True)]
            assert chunks == ["primary"]
