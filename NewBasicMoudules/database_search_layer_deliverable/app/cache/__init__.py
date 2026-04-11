# =====================================================
# AI外语学习系统 - 缓存模块
# 版本: 1.0.0
# =====================================================

from .redis_cache import RedisCache, create_cache

__all__ = [
    "RedisCache",
    "create_cache"
]
