"""Redis 缓存层测试"""

from __future__ import annotations

import pytest

from app.infrastructure.persistence.cache.redis_cache import RedisCache


@pytest.mark.asyncio
async def test_redis_cache_degrade_when_not_connected():
    cache = RedisCache(host="127.0.0.1", port=9999)
    assert await cache.connect() is False
    assert await cache.get("key") is None
    assert await cache.set("key", "value") is False
    assert await cache.delete("key") is False
    assert await cache.lock("key") is None


@pytest.mark.asyncio
async def test_redis_cache_get_or_set_degrade():
    cache = RedisCache(host="127.0.0.1", port=9999)
    called = False

    async def factory():
        nonlocal called
        called = True
        return "computed"

    result = await cache.get_or_set("key", factory)
    assert called is True
    assert result == "computed"
