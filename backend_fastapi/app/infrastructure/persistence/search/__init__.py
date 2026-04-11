"""搜索层实现"""

from __future__ import annotations

from typing import Any

from .es_client import ensure_index, get_es_client, index_document, search_vocabulary


class VocabularySearcher:
    """词汇搜索引擎"""

    def __init__(self, es_client: Any | None = None) -> None:
        self.es = es_client

    async def ensure_index(self) -> bool:
        if self.es is not None:
            return await ensure_index(client=self.es)
        return await ensure_index()

    async def index(self, doc: dict[str, Any], doc_id: str | None = None) -> bool:
        if self.es is not None:
            return await index_document(doc=doc, doc_id=doc_id, client=self.es)
        return await index_document(doc=doc, doc_id=doc_id)

    async def search(
        self,
        query: str,
        fuzzy: bool = True,
        expand_synonyms: bool = True,
        language: str = "en",
        size: int = 20,
    ) -> list[dict[str, Any]]:
        """搜索词汇"""
        if self.es is not None:
            return await search_vocabulary(query=query, fuzzy=fuzzy, size=size, client=self.es)
        return await search_vocabulary(query=query, fuzzy=fuzzy, size=size)


__all__ = [
    "VocabularySearcher",
    "get_es_client",
    "ensure_index",
    "index_document",
    "search_vocabulary",
]
