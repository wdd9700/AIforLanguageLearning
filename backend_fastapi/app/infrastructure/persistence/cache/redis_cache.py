"""Redis缓存模块"""

from __future__ import annotations

import logging
import pickle
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis缓存管理器（兼容层）"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        default_ttl: int = 300,
        key_prefix: str = "aifl:",
        startup_nodes: list[dict[str, Any]] | None = None,
    ):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.startup_nodes = startup_nodes or []
        self._client: Any | None = None
        self._connected = False

    async def connect(self) -> bool:
        """连接Redis（单机或Cluster预留）"""
        try:
            import redis.asyncio as redis

            if self.startup_nodes:
                self._client = redis.RedisCluster(
                    startup_nodes=self.startup_nodes,
                    password=self.password,
                    decode_responses=False,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    skip_full_coverage_check=True,
                )
            else:
                self._client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    decode_responses=False,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
            await self._client.ping()
            self._connected = True
            return True
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
            self._connected = False
            return False

    async def close(self) -> None:
        """关闭连接"""
        if self._client:
            await self._client.close()
            self._client = None
            self._connected = False

    def _make_key(self, key: str) -> str:
        return f"{self.key_prefix}{key}"

    def _serialize(self, value: Any) -> bytes:
        return pickle.dumps(value)

    def _deserialize(self, value: bytes) -> Any:
        return pickle.loads(value)

    async def get(self, key: str) -> Any | None:
        if not self._client or not self._connected:
            return None
        try:
            full_key = self._make_key(key)
            value = await self._client.get(full_key)
            if value:
                return self._deserialize(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        if not self._client or not self._connected:
            return False
        try:
            full_key = self._make_key(key)
            serialized = self._serialize(value)
            expiration = ttl or self.default_ttl
            await self._client.setex(full_key, expiration, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        if not self._client or not self._connected:
            return False
        try:
            full_key = self._make_key(key)
            result = await self._client.delete(full_key)
            return result > 0
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def lock(self, key: str, timeout: int = 10, blocking_timeout: float = 5.0) -> Any | None:
        """获取分布式锁；Redis不可用时返回None（静默降级）"""
        if not self._client or not self._connected:
            return None
        try:
            lock_key = self._make_key(f"lock:{key}")
            lock = self._client.lock(lock_key, timeout=timeout, blocking_timeout=blocking_timeout)
            acquired = await lock.acquire()
            if acquired:
                return lock
            return None
        except Exception as e:
            logger.error(f"Cache lock error: {e}")
            return None

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[Any]],
        ttl: Optional[int] = None,
    ) -> Any:
        """Cache-Aside: 先查缓存，未命中则调用factory并回写缓存"""
        cached = await self.get(key)
        if cached is not None:
            return cached
        value = await factory()
        await self.set(key, value, ttl=ttl)
        return value
