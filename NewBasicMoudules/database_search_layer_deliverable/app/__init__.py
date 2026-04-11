# =====================================================
# AI外语学习系统 - 数据库搜索层
# 版本: 1.0.0
# =====================================================

from .search import (
    VocabularySearcher,
    VocabularySearchResult,
    search_vocabulary,
    VOCABULARY_INDEX_MAPPING,
    SEARCH_CONFIG
)

from .cache import RedisCache, create_cache

__version__ = "1.0.0"

__all__ = [
    # 搜索模块
    "VocabularySearcher",
    "VocabularySearchResult",
    "search_vocabulary",
    "VOCABULARY_INDEX_MAPPING",
    "SEARCH_CONFIG",
    # 缓存模块
    "RedisCache",
    "create_cache"
]
