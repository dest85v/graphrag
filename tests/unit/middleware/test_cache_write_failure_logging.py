# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for cache write failure logging (001-middleware-exception-logging).

Verifies that cache.set() failures are logged with exception details
and do not break the LLM response.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from graphrag_llm.middleware.with_cache import with_cache
from graphrag_llm.types import LLMCompletionResponse


class FailingCache:
    """Cache that raises on set() calls."""

    def __init__(self, get_data: dict | None = None) -> None:
        self._data = get_data or {}
        self.set_calls = 0
        self.get_calls = 0

    async def get(self, key: str) -> Any:
        self.get_calls += 1
        return self._data.get(key)

    async def set(self, key: str, value: Any, debug_data: dict | None = None) -> None:
        self.set_calls += 1
        raise RuntimeError("Cache write failure: connection refused")

    async def has(self, key: str) -> bool:
        return key in self._data

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def clear(self) -> None:
        self._data.clear()

    def child(self, name: str):
        return FailingCache(self._data)


def _make_cache_key(input_args: dict[str, Any]) -> str:
    return str(hash(str(input_args)))


def _make_response() -> LLMCompletionResponse:
    from openai.types.chat.chat_completion import Choice
    from openai.types.chat.chat_completion_message import ChatCompletionMessage

    return LLMCompletionResponse(
        id="chatcmpl-test",
        object="chat.completion",
        created=1234567890,
        model="gpt-4o",
        choices=[
            Choice(
                index=0,
                message=ChatCompletionMessage(role="assistant", content="ok"),
                finish_reason="stop",
            ),
        ],
    )


class TestCacheWriteFailureLogging:
    """Tests for cache write failure logging (US1)."""

    def test_sync_cache_write_failure_logs_warning(self):
        """Sync path: cache.set() failure must be logged and response must still return.

        When cache.set() raises, the middleware should:
        1. Log the exception with full details
        2. Return the LLM response normally
        3. Not propagate the exception to the caller
        """
        cache = FailingCache()
        mock_fn = MagicMock(return_value=_make_response())

        wrapped_sync, _ = with_cache(
            sync_middleware=mock_fn,
            async_middleware=AsyncMock(return_value=_make_response()),
            request_type="chat",
            cache=cache,  # type: ignore[arg-type]
            cache_key_creator=_make_cache_key,  # type: ignore[arg-type]
        )

        with patch("graphrag_llm.middleware.with_cache.log") as mock_log:
            result = wrapped_sync(messages=[{"role": "user", "content": "hello"}])

        # Response must be returned
        assert result is not None
        assert hasattr(result, "choices"), f"Expected LLMCompletionResponse, got {type(result)}"
        assert result.choices[0].message.content == "ok"  # type: ignore[union-attr]
        # Exception must be logged
        mock_log.exception.assert_called_once()
        call_args = mock_log.exception.call_args[0][0]
        assert "cache" in call_args.lower() or "write" in call_args.lower()
        # LLM function must have been called
        mock_fn.assert_called_once()

    def test_async_cache_write_failure_logs_warning(self):
        """Async path: cache.set() failure must be logged and response must still return."""
        cache = FailingCache()
        mock_fn = AsyncMock(return_value=_make_response())

        _, wrapped_async = with_cache(
            sync_middleware=MagicMock(return_value=_make_response()),
            async_middleware=mock_fn,
            request_type="chat",
            cache=cache,  # type: ignore[arg-type]
            cache_key_creator=_make_cache_key,  # type: ignore[arg-type]
        )

        import asyncio

        with patch("graphrag_llm.middleware.with_cache.log") as mock_log:
            result = asyncio.get_event_loop().run_until_complete(
                wrapped_async(messages=[{"role": "user", "content": "hello"}])
            )

        # Response must be returned
        assert result is not None
        assert hasattr(result, "choices"), f"Expected LLMCompletionResponse, got {type(result)}"
        assert result.choices[0].message.content == "ok"  # type: ignore[union-attr]
        # Exception must be logged
        mock_log.exception.assert_called_once()
        call_args = mock_log.exception.call_args[0][0]
        assert "cache" in call_args.lower() or "write" in call_args.lower()
        mock_fn.assert_called_once()

    def test_sync_cache_write_failure_does_not_propagate(self):
        """Cache write failure must NOT propagate to the caller — response is returned."""
        cache = FailingCache()
        mock_fn = MagicMock(return_value=_make_response())

        wrapped_sync, _ = with_cache(
            sync_middleware=mock_fn,
            async_middleware=AsyncMock(return_value=_make_response()),
            request_type="chat",
            cache=cache,  # type: ignore[arg-type]
            cache_key_creator=_make_cache_key,  # type: ignore[arg-type]
        )

        # Must not raise
        result = wrapped_sync(messages=[{"role": "user", "content": "hello"}])
        assert isinstance(result, LLMCompletionResponse)

    def test_async_cache_write_failure_does_not_propagate(self):
        """Async cache write failure must NOT propagate to the caller."""
        cache = FailingCache()
        mock_fn = AsyncMock(return_value=_make_response())

        _, wrapped_async = with_cache(
            sync_middleware=MagicMock(return_value=_make_response()),
            async_middleware=mock_fn,
            request_type="chat",
            cache=cache,  # type: ignore[arg-type]
            cache_key_creator=_make_cache_key,  # type: ignore[arg-type]
        )

        import asyncio

        # Must not raise
        result = asyncio.get_event_loop().run_until_complete(
            wrapped_async(messages=[{"role": "user", "content": "hello"}])
        )
        assert isinstance(result, LLMCompletionResponse)
