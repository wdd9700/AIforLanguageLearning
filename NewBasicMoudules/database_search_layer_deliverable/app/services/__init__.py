# =====================================================
# AI外语学习系统 - 服务层
# 版本: 1.0.0
# =====================================================

from .vocabulary_service import VocabularyService
from .search_service import SearchService

__all__ = [
    "VocabularyService",
    "SearchService"
]
