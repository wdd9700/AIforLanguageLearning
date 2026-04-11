"""重试工具模块 - 提供指数退避重试机制

支持：
- 指数退避重试
- 自定义重试次数和间隔
- 特定异常类型的重试
- 重试回调函数
"""

from __future__ import annotations

import asyncio
import functools
import logging
import random
from typing import Any, Callable, TypeVar, cast

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryConfig:
    """重试配置"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    ):
        """
        初始化重试配置
        
        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟（秒）
            max_delay: 最大延迟（秒）
            exponential_base: 指数基数
            jitter: 是否添加随机抖动
            retryable_exceptions: 可重试的异常类型
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    计算重试延迟
    
    使用指数退避算法：delay = min(base_delay * (exponential_base ^ attempt), max_delay)
    
    Args:
        attempt: 当前尝试次数（从0开始）
        config: 重试配置
        
    Returns:
        float: 延迟秒数
    """
    delay = config.base_delay * (config.exponential_base ** attempt)
    delay = min(delay, config.max_delay)
    
    if config.jitter:
        # 添加±20%的随机抖动
        jitter_factor = 0.8 + random.random() * 0.4
        delay *= jitter_factor
    
    return delay


async def retry_async(
    func: Callable[..., T],
    *args: Any,
    config: RetryConfig | None = None,
    on_retry: Callable[[int, Exception, float], None] | None = None,
    **kwargs: Any
) -> T:
    """
    异步函数重试包装器
    
    Args:
        func: 要执行的异步函数
        *args: 函数参数
        config: 重试配置
        on_retry: 重试回调函数(attempt, exception, next_delay)
        **kwargs: 函数关键字参数
        
    Returns:
        T: 函数返回值
        
    Raises:
        Exception: 所有重试失败后抛出最后一次异常
    """
    config = config or RetryConfig()
    last_exception: Exception | None = None
    
    for attempt in range(config.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except config.retryable_exceptions as e:
            last_exception = e
            
            if attempt >= config.max_retries:
                logger.error(
                    f"Function {func.__name__} failed after {config.max_retries + 1} attempts. "
                    f"Last error: {e}"
                )
                raise
            
            delay = calculate_delay(attempt, config)
            
            logger.warning(
                f"Function {func.__name__} failed (attempt {attempt + 1}/{config.max_retries + 1}). "
                f"Retrying in {delay:.2f}s. Error: {e}"
            )
            
            if on_retry:
                on_retry(attempt + 1, e, delay)
            
            await asyncio.sleep(delay)
    
    # 不应该到达这里
    raise last_exception or RuntimeError("Unexpected retry loop exit")


def retry_sync(
    func: Callable[..., T],
    *args: Any,
    config: RetryConfig | None = None,
    on_retry: Callable[[int, Exception, float], None] | None = None,
    **kwargs: Any
) -> T:
    """
    同步函数重试包装器
    
    Args:
        func: 要执行的同步函数
        *args: 函数参数
        config: 重试配置
        on_retry: 重试回调函数
        **kwargs: 函数关键字参数
        
    Returns:
        T: 函数返回值
    """
    config = config or RetryConfig()
    last_exception: Exception | None = None
    
    for attempt in range(config.max_retries + 1):
        try:
            return func(*args, **kwargs)
        except config.retryable_exceptions as e:
            last_exception = e
            
            if attempt >= config.max_retries:
                logger.error(
                    f"Function {func.__name__} failed after {config.max_retries + 1} attempts"
                )
                raise
            
            delay = calculate_delay(attempt, config)
            
            logger.warning(
                f"Function {func.__name__} failed (attempt {attempt + 1}). "
                f"Retrying in {delay:.2f}s"
            )
            
            if on_retry:
                on_retry(attempt + 1, e, delay)
            
            # 同步sleep
            import time
            time.sleep(delay)
    
    raise last_exception or RuntimeError("Unexpected retry loop exit")


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    重试装饰器（支持同步和异步函数）
    
    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟
        max_delay: 最大延迟
        retryable_exceptions: 可重试的异常类型
        
    Returns:
        Callable: 装饰器函数
        
    Example:
        @with_retry(max_retries=3, base_delay=1.0)
        async def my_async_function():
            pass
            
        @with_retry(max_retries=3)
        def my_sync_function():
            pass
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        retryable_exceptions=retryable_exceptions,
    )
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            return await retry_async(func, *args, config=config, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            return retry_sync(func, *args, config=config, **kwargs)
        
        # 根据函数类型返回合适的包装器
        if asyncio.iscoroutinefunction(func):
            return cast(Callable[..., T], async_wrapper)
        else:
            return cast(Callable[..., T], sync_wrapper)
    
    return decorator


# 预定义的重试配置
RETRY_CONFIG_DEFAULT = RetryConfig(max_retries=3, base_delay=1.0)
RETRY_CONFIG_LLM_API = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0,
    retryable_exceptions=(
        ConnectionError,
        TimeoutError,
        Exception,  # httpx异常
    ),
)
RETRY_CONFIG_KIMI = RetryConfig(
    max_retries=3,
    base_delay=2.0,  # Kimi API可能需要更长的初始延迟
    max_delay=30.0,
    retryable_exceptions=(
        ConnectionError,
        TimeoutError,
        Exception,
    ),
)


__all__ = [
    "RetryConfig",
    "calculate_delay",
    "retry_async",
    "retry_sync",
    "with_retry",
    "RETRY_CONFIG_DEFAULT",
    "RETRY_CONFIG_LLM_API",
    "RETRY_CONFIG_KIMI",
]