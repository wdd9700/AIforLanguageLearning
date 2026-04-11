"""持久化层接口契约与实现占位"""

from __future__ import annotations

from typing import Any, Protocol


class VocabularySearchService(Protocol):
    """词汇搜索服务契约"""

    async def search(self, query: str, fuzzy: bool = True, limit: int = 20) -> list[dict[str, Any]]:
        ...


class CacheService(Protocol):
    """缓存服务契约"""

    async def get(self, key: str) -> str | None:
        ...

    async def set(self, key: str, value: str, ttl: int = 300) -> bool:
        ...

    async def delete(self, key: str) -> bool:
        ...


class PersistenceUnitOfWork(Protocol):
    """数据持久化工作单元契约"""

    async def get_vocabulary_by_word(self, word: str, language: str = "en") -> dict[str, Any] | None:
        ...

    async def upsert_vocabulary(self, data: dict[str, Any]) -> dict[str, Any]:
        ...
