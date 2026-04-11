"""Elasticsearch 搜索层测试"""

from __future__ import annotations

import pytest

from app.infrastructure.persistence.search import VocabularySearcher


@pytest.mark.asyncio
async def test_vocabulary_searcher_returns_list():
    searcher = VocabularySearcher()
    results = await searcher.search("apple")
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_vocabulary_searcher_empty_query():
    searcher = VocabularySearcher()
    results = await searcher.search("")
    assert isinstance(results, list)
