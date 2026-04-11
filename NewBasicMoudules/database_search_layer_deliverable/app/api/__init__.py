# =====================================================
# AI外语学习系统 - API路由层
# 版本: 1.0.0
# =====================================================

from .vocabulary_routes import router as vocabulary_router
from .search_routes import router as search_router

__all__ = [
    "vocabulary_router",
    "search_router"
]
