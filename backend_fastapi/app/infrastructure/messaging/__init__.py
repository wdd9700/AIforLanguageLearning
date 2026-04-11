"""消息队列层接口契约与实现占位"""

from __future__ import annotations

from typing import Any, AsyncIterator, Protocol


class MessageQueue(Protocol):
    """消息队列契约"""

    async def publish(self, queue: str, payload: dict[str, Any], priority: int = 5) -> bool:
        ...

    async def consume(self, queue: str) -> AsyncIterator[dict[str, Any]]:
        ...
