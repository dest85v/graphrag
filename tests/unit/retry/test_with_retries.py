# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

# pyright: reportArgumentType=false

"""Tests for retry middleware routing."""

from unittest.mock import AsyncMock, MagicMock

from graphrag_llm.middleware.with_retries import with_retries
from graphrag_llm.retry.exponential_retry import ExponentialRetry


def asyncio_run(coro):
    """Helper to run async functions in sync test context."""
    import asyncio

    return asyncio.run(coro)


class TestWithRetriesRouting:
    """Tests for the with_retries middleware routing logic."""

    def test_sync_middleware_routes_to_sync_retry(self) -> None:
        """Verify sync middleware routes to retrier.retry()."""
        retrier = MagicMock(spec=ExponentialRetry)
        retrier.retry = MagicMock(return_value="result")

        def sync_func(**kwargs: dict) -> str:
            return "inner"

        sync_func_2 = sync_func
        async_func_2 = AsyncMock()

        sync_middleware = with_retries(  
            sync_middleware=sync_func_2, async_middleware=async_func_2, retrier=retrier
        )[0]

        result = sync_middleware(arg1="value")

        assert result == "result"
        retrier.retry.assert_called_once()
        call_kwargs = retrier.retry.call_args
        assert call_kwargs.kwargs["func"] == sync_func_2
        assert call_kwargs.kwargs["input_args"] == {"arg1": "value"}

    def test_async_middleware_routes_to_async_retry(self) -> None:
        """Verify async middleware routes to retrier.retry_async()."""
        retrier = MagicMock(spec=ExponentialRetry)
        retrier.retry_async = AsyncMock(return_value="result")

        async def async_func(**kwargs: dict) -> str:
            return "inner"

        sync_func_2 = MagicMock()
        async_middleware = with_retries(  
            sync_middleware=sync_func_2, async_middleware=async_func, retrier=retrier
        )[1]

        result = asyncio_run(async_middleware(arg2=42))

        assert result == "result"
        retrier.retry_async.assert_called_once()
        call_kwargs = retrier.retry_async.call_args
        assert call_kwargs.kwargs["func"] == async_func
        assert call_kwargs.kwargs["input_args"] == {"arg2": 42}

    def test_sync_path_calls_inner_function(self) -> None:
        """Verify sync path correctly passes kwargs to inner function."""
        retrier = MagicMock(spec=ExponentialRetry)
        retrier.retry = MagicMock(return_value="retry_result")

        def sync_func(**kwargs: dict) -> str:
            return f"inner_{kwargs.get('key', '')}"

        sync_middleware = with_retries(  
            sync_middleware=sync_func, async_middleware=AsyncMock(), retrier=retrier
        )[0]

        sync_middleware(key="test")

        # retrier.retry should be called with the inner function
        assert retrier.retry.call_args.kwargs["func"] == sync_func

    def test_async_path_calls_inner_function(self) -> None:
        """Verify async path correctly passes kwargs to inner function."""
        retrier = MagicMock(spec=ExponentialRetry)
        retrier.retry_async = AsyncMock(return_value="retry_result")

        async def async_func(**kwargs: dict) -> str:
            return f"inner_{kwargs.get('key', '')}"

        async_middleware = with_retries(  
            sync_middleware=MagicMock(), async_middleware=async_func, retrier=retrier
        )[1]

        asyncio_run(async_middleware(key="test"))

        # retrier.retry_async should be called with the inner function
        assert retrier.retry_async.call_args.kwargs["func"] == async_func

    def test_sync_path_returns_retrier_result(self) -> None:
        """Verify sync path returns the retrier's result."""
        retrier = MagicMock(spec=ExponentialRetry)
        retrier.retry = MagicMock(return_value="from_sync_retry")

        def sync_func(**kwargs: dict) -> str:
            return "should_not_reach_here"

        sync_middleware = with_retries(  
            sync_middleware=sync_func, async_middleware=AsyncMock(), retrier=retrier
        )[0]

        result = sync_middleware(x=1)
        assert result == "from_sync_retry"

    def test_async_path_returns_retrier_result(self) -> None:
        """Verify async path returns the retrier's result."""
        retrier = MagicMock(spec=ExponentialRetry)
        retrier.retry_async = AsyncMock(return_value="from_async_retry")

        async def async_func(**kwargs: dict) -> str:
            return "should_not_reach_here"

        async_middleware = with_retries(  
            sync_middleware=MagicMock(), async_middleware=async_func, retrier=retrier
        )[1]

        result = asyncio_run(async_middleware(x=2))
        assert result == "from_async_retry"
