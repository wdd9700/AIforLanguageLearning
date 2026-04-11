# =====================================================
# AI外语学习系统 - Redis缓存模块
# 版本: 1.0.0
# 描述: 提供缓存管理、分布式锁、防止缓存击穿等功能
# =====================================================

import json
import logging
import pickle
from typing import Any, Optional, List, Dict, Union
from contextlib import asynccontextmanager
from datetime import timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedisCache:
    """
    Redis缓存管理器
    
    功能：
    1. 基础缓存操作（get/set/delete）
    2. 分布式锁（防止缓存击穿）
    3. 缓存预热
    4. 批量操作
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        default_ttl: int = 300,
        key_prefix: str = "aifl:"
    ):
        """
        初始化Redis缓存
        
        Args:
            host: Redis主机
            port: Redis端口
            db: 数据库编号
            password: 密码
            default_ttl: 默认过期时间（秒）
            key_prefix: 键前缀
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self._client = None
    
    async def connect(self):
        """连接Redis"""
        try:
            import redis.asyncio as redis
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            await self._client.ping()
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
        except ImportError:
            logger.error("redis package not installed. Run: pip install redis")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.close()
    
    def _make_key(self, key: str) -> str:
        """生成带前缀的键"""
        return f"{self.key_prefix}{key}"
    
    def _serialize(self, value: Any) -> bytes:
        """序列化值"""
        return pickle.dumps(value)
    
    def _deserialize(self, value: bytes) -> Any:
        """反序列化值"""
        return pickle.loads(value)
    
    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值或None
        """
        if not self._client:
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
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False
    ) -> bool:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
            nx: 仅在键不存在时设置
            
        Returns:
            是否设置成功
        """
        if not self._client:
            return False
        
        try:
            full_key = self._make_key(key)
            serialized = self._serialize(value)
            expiration = ttl or self.default_ttl
            
            if nx:
                result = await self._client.setnx(full_key, serialized)
                if result:
                    await self._client.expire(full_key, expiration)
                return result
            else:
                await self._client.setex(full_key, expiration, serialized)
                return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
            
        Returns:
            是否删除成功
        """
        if not self._client:
            return False
        
        try:
            full_key = self._make_key(key)
            result = await self._client.delete(full_key)
            return result > 0
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            是否存在
        """
        if not self._client:
            return False
        
        try:
            full_key = self._make_key(key)
            return await self._client.exists(full_key) > 0
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """
        设置过期时间
        
        Args:
            key: 缓存键
            ttl: 过期时间（秒）
            
        Returns:
            是否设置成功
        """
        if not self._client:
            return False
        
        try:
            full_key = self._make_key(key)
            return await self._client.expire(full_key, ttl)
        except Exception as e:
            logger.error(f"Cache expire error: {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """
        获取剩余过期时间
        
        Args:
            key: 缓存键
            
        Returns:
            剩余秒数，-1表示永不过期，-2表示不存在
        """
        if not self._client:
            return -2
        
        try:
            full_key = self._make_key(key)
            return await self._client.ttl(full_key)
        except Exception as e:
            logger.error(f"Cache ttl error: {e}")
            return -2
    
    # -------------------------------------------------
    # 分布式锁（防止缓存击穿）
    # -------------------------------------------------
    
    @asynccontextmanager
    async def lock(
        self,
        lock_key: str,
        timeout: int = 10,
        blocking: bool = True,
        blocking_timeout: int = 10
    ):
        """
        分布式锁上下文管理器
        
        用于防止缓存击穿：当缓存失效时，只有一个请求能重建缓存
        
        Args:
            lock_key: 锁键
            timeout: 锁超时时间（秒）
            blocking: 是否阻塞等待
            blocking_timeout: 阻塞等待超时时间
            
        Example:
            async with cache.lock("vocab:hello", timeout=30):
                # 只有一个请求能执行到这里
                data = await fetch_from_db()
                await cache.set("vocab:hello", data)
        """
        if not self._client:
            yield None
            return
        
        full_key = self._make_key(f"lock:{lock_key}")
        lock_value = f"{timeout}"
        
        try:
            # 尝试获取锁
            acquired = await self._client.set(
                full_key,
                lock_value,
                nx=True,
                ex=timeout
            )
            
            if not acquired and blocking:
                # 阻塞等待锁
                import asyncio
                start_time = asyncio.get_event_loop().time()
                while not acquired:
                    await asyncio.sleep(0.1)
                    acquired = await self._client.set(
                        full_key,
                        lock_value,
                        nx=True,
                        ex=timeout
                    )
                    if asyncio.get_event_loop().time() - start_time > blocking_timeout:
                        raise TimeoutError(f"Could not acquire lock for {lock_key}")
            
            yield acquired
            
        finally:
            # 释放锁
            if self._client:
                await self._client.delete(full_key)
    
    async def acquire_lock(self, lock_key: str, timeout: int = 10) -> Optional[str]:
        """
        获取分布式锁（非阻塞）
        
        Args:
            lock_key: 锁键
            timeout: 锁超时时间
            
        Returns:
            锁标识符（用于释放锁）或None
        """
        if not self._client:
            return None
        
        import uuid
        lock_value = str(uuid.uuid4())
        full_key = self._make_key(f"lock:{lock_key}")
        
        acquired = await self._client.set(full_key, lock_value, nx=True, ex=timeout)
        return lock_value if acquired else None
    
    async def release_lock(self, lock_key: str, lock_value: str) -> bool:
        """
        释放分布式锁
        
        Args:
            lock_key: 锁键
            lock_value: 锁标识符
            
        Returns:
            是否释放成功
        """
        if not self._client:
            return False
        
        full_key = self._make_key(f"lock:{lock_key}")
        
        # 使用Lua脚本确保原子性
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        result = await self._client.eval(lua_script, 1, full_key, lock_value)
        return result == 1
    
    # -------------------------------------------------
    # 缓存装饰器模式
    # -------------------------------------------------
    
    def cached(
        self,
        ttl: Optional[int] = None,
        key_prefix: str = "",
        skip_cache: Optional[callable] = None
    ):
        """
        缓存装饰器
        
        Args:
            ttl: 缓存过期时间
            key_prefix: 键前缀
            skip_cache: 是否跳过缓存的判断函数
            
        Example:
            @cache.cached(ttl=300, key_prefix="vocab")
            async def get_vocabulary(word: str):
                return await fetch_from_db(word)
        """
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # 生成缓存键
                cache_key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
                
                # 检查是否跳过缓存
                if skip_cache and skip_cache(*args, **kwargs):
                    return await func(*args, **kwargs)
                
                # 尝试从缓存获取
                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_value
                
                # 使用分布式锁防止缓存击穿
                async with self.lock(cache_key, timeout=30):
                    # 双重检查
                    cached_value = await self.get(cache_key)
                    if cached_value is not None:
                        return cached_value
                    
                    # 执行函数
                    result = await func(*args, **kwargs)
                    
                    # 写入缓存
                    if result is not None:
                        await self.set(cache_key, result, ttl)
                    
                    return result
            
            return wrapper
        return decorator
    
    # -------------------------------------------------
    # 批量操作
    # -------------------------------------------------
    
    async def mget(self, keys: List[str]) -> List[Optional[Any]]:
        """
        批量获取
        
        Args:
            keys: 键列表
            
        Returns:
            值列表
        """
        if not self._client:
            return [None] * len(keys)
        
        try:
            full_keys = [self._make_key(k) for k in keys]
            values = await self._client.mget(full_keys)
            return [
                self._deserialize(v) if v else None
                for v in values
            ]
        except Exception as e:
            logger.error(f"Cache mget error: {e}")
            return [None] * len(keys)
    
    async def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        批量设置
        
        Args:
            mapping: 键值映射
            ttl: 过期时间
            
        Returns:
            是否设置成功
        """
        if not self._client:
            return False
        
        try:
            pipe = self._client.pipeline()
            expiration = ttl or self.default_ttl
            
            for key, value in mapping.items():
                full_key = self._make_key(key)
                serialized = self._serialize(value)
                pipe.setex(full_key, expiration, serialized)
            
            await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Cache mset error: {e}")
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的所有键
        
        Args:
            pattern: 匹配模式（如 "vocab:*"）
            
        Returns:
            删除的键数量
        """
        if not self._client:
            return 0
        
        try:
            full_pattern = self._make_key(pattern)
            keys = []
            async for key in self._client.scan_iter(match=full_pattern):
                keys.append(key)
            
            if keys:
                await self._client.delete(*keys)
            
            return len(keys)
        except Exception as e:
            logger.error(f"Cache delete_pattern error: {e}")
            return 0
    
    # -------------------------------------------------
    # 缓存统计
    # -------------------------------------------------
    
    async def info(self) -> Dict[str, Any]:
        """
        获取Redis信息
        
        Returns:
            Redis服务器信息
        """
        if not self._client:
            return {}
        
        try:
            info = await self._client.info()
            return info
        except Exception as e:
            logger.error(f"Cache info error: {e}")
            return {}
    
    async def dbsize(self) -> int:
        """
        获取当前数据库键数量
        
        Returns:
            键数量
        """
        if not self._client:
            return 0
        
        try:
            return await self._client.dbsize()
        except Exception as e:
            logger.error(f"Cache dbsize error: {e}")
            return 0


# 便捷函数
async def create_cache(
    host: str = "localhost",
    port: int = 6379,
    **kwargs
) -> RedisCache:
    """
    创建并连接缓存实例
    
    Args:
        host: Redis主机
        port: Redis端口
        **kwargs: 其他参数
        
    Returns:
        已连接的RedisCache实例
    """
    cache = RedisCache(host=host, port=port, **kwargs)
    await cache.connect()
    return cache
