# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for cache middleware event loop handling (013-event-loop fix).

Verifies that the with_cache middleware does not create a new event loop
per invocation, preventing event loop accumulation under load.
"""

import asyncio
import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from graphrag_llm.middleware.with_cache import with_cache
from graphrag_llm.types import LLMCompletionResponse


class MockCache:
    """Minimal mock cache for testing event loop behavior."""

    def __init__(self, data: dict | None = None):
        self._data = data or {}
        self.get_calls = 0
        self.set_calls = 0

    async def get(self, key: str) -> Any:
        self.get_calls += 1
        return self._data.get(key)

    async def set(self, key: str, value: Any, debug_data: dict | None = None) -> None:
        self.set_calls += 1
        self._data[key] = value

    async def has(self, key: str) -> bool:
        return key in self._data

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def clear(self) -> None:
        self._data.clear()

    def child(self, name: str):
        return MockCache(self._data)


def _make_cache_key(input_args: dict[str, Any]) -> str:
    """Simple cache key creator."""
    return str(hash(str(input_args)))


def _make_mock_sync_fn(response):
    """Create a mock sync LLM function."""
    return MagicMock(return_value=response)


def _make_mock_async_fn(response):
    """Create a mock async LLM function."""
    return AsyncMock(return_value=response)


class TestCacheEventLoopLeak:
    """Tests for event loop leak prevention in cache middleware."""

    def _make_response(self):
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
                    message=ChatCompletionMessage(role="assistant", content="test"),
                    finish_reason="stop",
                ),
            ],
        )

    def test_no_event_loop_leak_under_load(self):
        """Cache middleware must not leak event loops under repeated sync calls.

        The current broken implementation creates a new event loop on every
        cache get/set. This test verifies that after 100 sequential sync
        cache middleware calls, no EventLoop objects accumulate.
        """
        response = self._make_response()
        cache = MockCache()
        sync_fn = _make_mock_sync_fn(response)
        async_fn = _make_mock_async_fn(response)

        wrapped_sync, _ = with_cache(  # type: ignore[arg-type]
            sync_middleware=sync_fn,
            async_middleware=async_fn,
            request_type="chat",
            cache=cache,  # type: ignore[arg-type]
            cache_key_creator=_make_cache_key,  # type: ignore[arg-type]
        )

        # Collect event loop objects before calls
        gc.collect()
        loops_before = len([
            o for o in gc.get_objects() if isinstance(o, asyncio.AbstractEventLoop)
        ])

        # Make 100 sequential sync calls (all cache misses → triggers cache.set)
        for _ in range(100):
            wrapped_sync(messages=[{"role": "user", "content": f"msg_{_}"}])

        gc.collect()
        loops_after = len([
            o for o in gc.get_objects() if isinstance(o, asyncio.AbstractEventLoop)
        ])

        # Event loop count must not grow — the fix should reuse/create-close properly
        assert loops_after <= loops_before + 1, (
            f"Event loop count grew from {loops_before} to {loops_after} "
            f"after 100 sync calls — event loop leak detected"
        )
        assert sync_fn.call_count == 100, "All 100 sync calls must execute"
        assert cache.set_calls == 100, "All 100 calls must write to cache"

    def test_sync_entry_point_creates_new_loop(self):
        """When called from a sync entry point (no running loop), the helper must create and close a new loop."""
        from graphrag_llm.middleware._event_loop import run_async_in_loop

        created = []
        closed = []

        original_new = asyncio.new_event_loop
        original_close = asyncio.BaseEventLoop.close

        def track_new():
            loop = original_new()
            created.append(loop)
            return loop

        def track_close(self):
            if self in created:
                closed.append(self)
            return original_close(self)

        # Patch at module level where run_async_in_loop imports them
        with (
            patch(
                "graphrag_llm.middleware._event_loop.asyncio.new_event_loop",
                side_effect=track_new,
            ),
            patch.object(asyncio.BaseEventLoop, "close", track_close),
        ):

            def sync_entry_point():
                return run_async_in_loop(asyncio.sleep(0, result="done"))

            sync_entry_point()

        # Verify: a new loop was created and properly closed
        assert len(created) == 1, "Exactly one new event loop should be created"
        assert len(closed) == 1, "The created event loop must be closed"
        assert created[0] is closed[0], "The same loop must be created and closed"
