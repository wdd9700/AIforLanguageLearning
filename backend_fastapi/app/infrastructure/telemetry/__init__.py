"""遥测层接口契约与实现占位"""

from __future__ import annotations

from typing import Any, Protocol

from fastapi import Request


class MetricsCollector(Protocol):
    """指标收集契约"""

    def increment_request_count(self, method: str, path: str, status: int) -> None:
        ...

    def observe_request_latency(self, method: str, path: str, duration_ms: float) -> None:
        ...

    def increment_error_count(self, error_type: str) -> None:
        ...


class TelemetryMiddleware(Protocol):
    """遥测中间件契约"""

    async def process_request(self, request: Request) -> dict[str, Any]:
        ...
