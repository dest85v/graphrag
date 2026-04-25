# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Integration test: async retry does not block event loop."""

import asyncio
import time
from unittest.mock import patch

import pytest
from graphrag_llm.retry.exponential_retry import ExponentialRetry

_PATCH_TARGET = "graphrag_llm.retry.exponential_retry.asyncio.sleep"


class TestAsyncRetryEventLoopResponsiveness:
    """Integration tests verifying async retry does not block the event loop."""

    @pytest.mark.asyncio
    async def test_async_retry_does_not_block_event_loop(self) -> None:
        """Verify that async retry backoff does not block other concurrent requests."""
        retrier = ExponentialRetry(
            max_retries=1, base_delay=0.1, jitter=False, max_delay=0.5
        )

        results: dict[int, float] = {}
        sleep_delays_recorded: list[float] = []

        async def mock_sleep(delay: float) -> None:
            sleep_delays_recorded.append(delay)

        async def failing_task(task_id: int) -> float:
            start = time.monotonic()

            if task_id == 0:
                async def failing_call(**kwargs: dict) -> str:
                    raise ValueError("rate limited")

                with patch(_PATCH_TARGET, mock_sleep):
                    try:
                        await retrier.retry_async(
                            func=failing_call,
                            input_args={},
                        )
                    except ValueError:
                        pass

                results[task_id] = time.monotonic() - start
                return results[task_id]

            results[task_id] = time.monotonic() - start
            return results[task_id]

        start = time.monotonic()
        await asyncio.gather(*(failing_task(i) for i in range(5)))
        total_time = time.monotonic() - start

        for task_id, elapsed in results.items():
            assert elapsed < 0.5, f"Task {task_id} took {elapsed}s — too slow"

        assert sleep_delays_recorded == [0.1]

    @pytest.mark.asyncio
    async def test_concurrent_tasks_complete_without_retry_delay(self) -> None:
        """Verify concurrent non-retrying tasks are unaffected by a retrying task."""
        retrier = ExponentialRetry(
            max_retries=2, base_delay=0.05, jitter=False, max_delay=0.5
        )

        non_retrying_durations: list[float] = []
        sleep_delays_recorded: list[float] = []

        async def mock_sleep(delay: float) -> None:
            sleep_delays_recorded.append(delay)

        async def non_retrying_task(task_id: int) -> float:
            start = time.monotonic()
            await asyncio.sleep(0.01)
            duration = time.monotonic() - start
            non_retrying_durations.append(duration)
            return duration

        async def retrying_task() -> float:
            start = time.monotonic()

            async def failing_call(**kwargs: dict) -> str:
                raise ValueError("rate limited")

            with patch(_PATCH_TARGET, mock_sleep):
                try:
                    await retrier.retry_async(
                        func=failing_call,
                        input_args={},
                    )
                except ValueError:
                    pass

            return time.monotonic() - start

        start = time.monotonic()
        await asyncio.gather(
            retrying_task(),
            non_retrying_task(1),
            non_retrying_task(2),
            non_retrying_task(3),
        )
        total_time = time.monotonic() - start

        for duration in non_retrying_durations:
            assert duration < 0.1, f"Non-retrying task took {duration}s"

        assert total_time < 0.5, f"All tasks took {total_time}s — too long"

    @pytest.mark.asyncio
    async def test_async_sleep_mock_called_with_correct_delays(self) -> None:
        """Verify asyncio.sleep is called with the correct exponential delays."""
        retrier = ExponentialRetry(
            max_retries=3, base_delay=0.5, jitter=False, max_delay=10.0
        )
        sleep_delays_recorded: list[float] = []

        async def mock_sleep(delay: float) -> None:
            sleep_delays_recorded.append(delay)

        async def failing_call(**kwargs: dict) -> str:
            raise ValueError("rate limited")

        with patch(_PATCH_TARGET, mock_sleep):
            with pytest.raises(ValueError, match="rate limited"):
                await retrier.retry_async(func=failing_call, input_args={})

        assert len(sleep_delays_recorded) == 3
        expected_delays = [0.5, 0.25, 0.125]
        assert sleep_delays_recorded == expected_delays

    @pytest.mark.asyncio
    async def test_async_retry_preserves_backoff_calculation(self) -> None:
        """Verify the backoff calculation is preserved in async path."""
        retrier = ExponentialRetry(
            max_retries=4, base_delay=2.0, jitter=False, max_delay=100.0
        )
        sleep_delays_recorded: list[float] = []

        async def mock_sleep(delay: float) -> None:
            sleep_delays_recorded.append(delay)

        async def failing_call(**kwargs: dict) -> str:
            raise ValueError("rate limited")

        with patch(_PATCH_TARGET, mock_sleep):
            with pytest.raises(ValueError, match="rate limited"):
                await retrier.retry_async(func=failing_call, input_args={})

        assert len(sleep_delays_recorded) == 4
        expected_delays = [2.0, 4.0, 8.0, 16.0]
        assert sleep_delays_recorded == expected_delays
