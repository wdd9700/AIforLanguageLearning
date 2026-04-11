# =====================================================
# AI外语学习系统 - 搜索模块
# 版本: 1.0.0
# =====================================================

from .es_config import (
    VOCABULARY_INDEX_MAPPING,
    SYNONYM_INDEX_MAPPING,
    SUGGESTION_INDEX_MAPPING,
    INDEX_NAMES,
    SEARCH_CONFIG,
    get_vocabulary_index_settings,
    get_synonym_index_settings,
    get_suggestion_index_settings,
    get_index_name
)

from .es_client import (
    ElasticsearchClient,
    get_es_client,
    es_client_context
)

from .vocabulary_search import (
    VocabularySearcher,
    VocabularySearchResult,
    search_vocabulary,
    get_suggestions,
    get_synonyms
)

from .vocabulary_indexer import (
    VocabularyIndexer,
    VocabularyEntry,
    bulk_index_vocabulary
)

__all__ = [
    # 配置
    "VOCABULARY_INDEX_MAPPING",
    "SYNONYM_INDEX_MAPPING",
    "SUGGESTION_INDEX_MAPPING",
    "INDEX_NAMES",
    "SEARCH_CONFIG",
    "get_vocabulary_index_settings",
    "get_synonym_index_settings",
    "get_suggestion_index_settings",
    "get_index_name",
    # ES客户端
    "ElasticsearchClient",
    "get_es_client",
    "es_client_context",
    # 搜索
    "VocabularySearcher",
    "VocabularySearchResult",
    "search_vocabulary",
    "get_suggestions",
    "get_synonyms",
    # 索引
    "VocabularyIndexer",
    "VocabularyEntry",
    "bulk_index_vocabulary"
]
