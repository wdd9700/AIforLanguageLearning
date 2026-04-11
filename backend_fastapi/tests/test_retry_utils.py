"""重试工具模块测试"""

from __future__ import annotations

import pytest

from app.retry_utils import (
    RetryConfig,
    calculate_delay,
    retry_async,
    retry_sync,
    with_retry,
)


class TestRetryConfig:
    """重试配置测试"""

    def test_default_config(self) -> None:
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_custom_config(self) -> None:
        config = RetryConfig(max_retries=5, base_delay=0.5, max_delay=10.0)
        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 10.0


class TestCalculateDelay:
    """延迟计算测试"""

    def test_exponential_backoff(self) -> None:
        config = RetryConfig(jitter=False)
        assert calculate_delay(0, config) == 1.0
        assert calculate_delay(1, config) == 2.0
        assert calculate_delay(2, config) == 4.0
        assert calculate_delay(3, config) == 8.0

    def test_max_delay_cap(self) -> None:
        config = RetryConfig(base_delay=1.0, max_delay=5.0, jitter=False)
        assert calculate_delay(10, config) == 5.0

    def test_jitter_range(self) -> None:
        config = RetryConfig(jitter=True)
        delay = calculate_delay(0, config)
        assert 0.8 <= delay <= 1.4


class TestRetryAsync:
    """异步重试测试"""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self) -> None:
        async def success_func() -> str:
            return "ok"

        result = await retry_async(success_func)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_retry_then_success(self) -> None:
        attempts = 0

        async def flaky_func() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ConnectionError("fail")
            return "ok"

        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
        result = await retry_async(flaky_func, config=config)
        assert result == "ok"
        assert attempts == 3

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self) -> None:
        async def always_fail() -> None:
            raise ValueError("always fail")

        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)
        with pytest.raises(ValueError, match="always fail"):
            await retry_async(always_fail, config=config)

    @pytest.mark.asyncio
    async def test_non_retryable_exception(self) -> None:
        async def raise_type_error() -> None:
            raise TypeError("not retryable")

        config = RetryConfig(
            max_retries=2, base_delay=0.01, retryable_exceptions=(ValueError,), jitter=False
        )
        with pytest.raises(TypeError, match="not retryable"):
            await retry_async(raise_type_error, config=config)


class TestRetrySync:
    """同步重试测试"""

    def test_success_on_first_attempt(self) -> None:
        def success_func() -> str:
            return "ok"

        result = retry_sync(success_func)
        assert result == "ok"

    def test_retry_then_success(self) -> None:
        attempts = 0

        def flaky_func() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ConnectionError("fail")
            return "ok"

        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
        result = retry_sync(flaky_func, config=config)
        assert result == "ok"
        assert attempts == 3


class TestWithRetryDecorator:
    """重试装饰器测试"""

    @pytest.mark.asyncio
    async def test_async_decorator(self) -> None:
        attempts = 0

        @with_retry(max_retries=2, base_delay=0.01)
        async def async_flaky() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise ConnectionError("fail")
            return "ok"

        result = await async_flaky()
        assert result == "ok"
        assert attempts == 2

    def test_sync_decorator(self) -> None:
        attempts = 0

        @with_retry(max_retries=2, base_delay=0.01)
        def sync_flaky() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise ConnectionError("fail")
            return "ok"

        result = sync_flaky()
        assert result == "ok"
        assert attempts == 2
