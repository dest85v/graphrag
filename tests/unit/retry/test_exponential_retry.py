# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Tests for ExponentialRetry async/sync sleep behavior."""

from unittest.mock import patch

import pytest
from graphrag_llm.retry.exponential_retry import ExponentialRetry


class TestExponentialRetrySyncPath:
    """Tests for the synchronous retry path."""

    def test_sync_retry_uses_time_sleep(self) -> None:
        """Verify that sync retry path uses time.sleep for backoff."""
        retrier = ExponentialRetry(max_retries=3, base_delay=1.0, jitter=False)
        call_count = 0

        def failing_func(**kwargs: dict) -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("transient error")
            return "success"

        with patch("time.sleep") as mock_sleep:
            result = retrier.retry(func=failing_func, input_args={})

        assert result == "success"
        assert call_count == 3
        # Verify time.sleep was called for the 2 retries
        assert mock_sleep.call_count == 2

    def test_sync_retry_sleep_delay_values(self) -> None:
        """Verify sync retry uses correct exponential delay values."""
        retrier = ExponentialRetry(
            max_retries=5, base_delay=2.0, jitter=False, max_delay=100.0
        )
        call_count = 0

        def always_fail(**kwargs: dict) -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("persistent error")

        with patch("time.sleep") as mock_sleep:
            with pytest.raises(ValueError, match="persistent error"):
                retrier.retry(func=always_fail, input_args={})

        assert call_count == 6  # initial + 5 retries
        # Verify sleep was called 5 times with expected delays
        assert mock_sleep.call_count == 5
        # With jitter=False and base_delay=2.0, delays should be: 2, 4, 8, 16, 32
        expected_delays = [2.0, 4.0, 8.0, 16.0, 32.0]
        actual_calls = [call[0][0] for call in mock_sleep.call_args_list]
        for expected, actual in zip(expected_delays, actual_calls):
            assert actual == expected

    def test_sync_retry_respects_max_delay(self) -> None:
        """Verify sync retry caps delays at max_delay."""
        retrier = ExponentialRetry(
            max_retries=10, base_delay=10.0, jitter=False, max_delay=15.0
        )
        call_count = 0

        def always_fail(**kwargs: dict) -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("persistent error")

        with patch("time.sleep") as mock_sleep:
            with pytest.raises(ValueError, match="persistent error"):
                retrier.retry(func=always_fail, input_args={})

        # All delays should be capped at max_delay=15.0
        actual_calls = [call[0][0] for call in mock_sleep.call_args_list]
        for delay in actual_calls:
            assert delay <= 15.0

    def test_sync_retry_does_not_retry_skipped_exceptions(self) -> None:
        """Verify that exceptions_to_skip are not retried."""
        retrier = ExponentialRetry(
            max_retries=5,
            base_delay=1.0,
            jitter=False,
            exceptions_to_skip=["ValueError"],
        )
        call_count = 0

        def failing_func(**kwargs: dict) -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("should not retry")

        with patch("time.sleep") as mock_sleep:
            with pytest.raises(ValueError, match="should not retry"):
                retrier.retry(func=failing_func, input_args={})

        assert call_count == 1  # only called once, no retries
        assert mock_sleep.call_count == 0

    def test_sync_retry_metrics_updated(self) -> None:
        """Verify metrics dict is updated on sync retry."""
        retrier = ExponentialRetry(max_retries=3, base_delay=1.0, jitter=False)
        call_count = 0
        metrics: dict = {}

        def failing_func(**kwargs: dict) -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("transient error")
            return "success"

        retrier.retry(func=failing_func, input_args={"metrics": metrics})

        assert metrics["retries"] == 1
        assert metrics["requests_with_retries"] == 1

    def test_sync_retry_metrics_no_retries(self) -> None:
        """Verify metrics show zero retries on first success."""
        retrier = ExponentialRetry(max_retries=3, base_delay=1.0, jitter=False)
        metrics: dict = {}

        def success_func(**kwargs: dict) -> str:
            return "success"

        retrier.retry(func=success_func, input_args={"metrics": metrics})

        assert metrics["retries"] == 0
        assert metrics["requests_with_retries"] == 0


class TestExponentialRetryAsyncPath:
    """Tests for the asynchronous retry path."""

    @pytest.mark.asyncio
    async def test_async_retry_uses_asyncio_sleep(self) -> None:
        """Verify that async retry path uses asyncio.sleep for backoff."""
        retrier = ExponentialRetry(max_retries=3, base_delay=1.0, jitter=False)
        call_count = 0

        async def failing_func(**kwargs: dict) -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("transient error")
            return "success"

        with patch("asyncio.sleep") as mock_sleep:
            result = await retrier.retry_async(
                func=failing_func, input_args={}
            )

        assert result == "success"
        assert call_count == 3
        # Verify asyncio.sleep was called for the 2 retries
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_async_retry_sleep_delay_values(self) -> None:
        """Verify async retry uses correct exponential delay values."""
        retrier = ExponentialRetry(
            max_retries=5, base_delay=2.0, jitter=False, max_delay=100.0
        )
        call_count = 0

        async def always_fail(**kwargs: dict) -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("persistent error")

        with patch("asyncio.sleep") as mock_sleep:
            with pytest.raises(ValueError, match="persistent error"):
                await retrier.retry_async(func=always_fail, input_args={})

        assert call_count == 6  # initial + 5 retries
        assert mock_sleep.call_count == 5
        # With jitter=False and base_delay=2.0, delays should be: 2, 4, 8, 16, 32
        expected_delays = [2.0, 4.0, 8.0, 16.0, 32.0]
        actual_calls = [call[0][0] for call in mock_sleep.call_args_list]
        for expected, actual in zip(expected_delays, actual_calls):
            assert actual == expected

    @pytest.mark.asyncio
    async def test_async_retry_respects_max_delay(self) -> None:
        """Verify async retry caps delays at max_delay."""
        retrier = ExponentialRetry(
            max_retries=10, base_delay=10.0, jitter=False, max_delay=15.0
        )
        call_count = 0

        async def always_fail(**kwargs: dict) -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("persistent error")

        with patch("asyncio.sleep") as mock_sleep:
            with pytest.raises(ValueError, match="persistent error"):
                await retrier.retry_async(func=always_fail, input_args={})

        # All delays should be capped at max_delay=15.0
        actual_calls = [call[0][0] for call in mock_sleep.call_args_list]
        for delay in actual_calls:
            assert delay <= 15.0

    @pytest.mark.asyncio
    async def test_async_retry_does_not_retry_skipped_exceptions(self) -> None:
        """Verify that exceptions_to_skip are not retried in async path."""
        retrier = ExponentialRetry(
            max_retries=5,
            base_delay=1.0,
            jitter=False,
            exceptions_to_skip=["ValueError"],
        )
        call_count = 0

        async def failing_func(**kwargs: dict) -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("should not retry")

        with patch("asyncio.sleep") as mock_sleep:
            with pytest.raises(ValueError, match="should not retry"):
                await retrier.retry_async(func=failing_func, input_args={})

        assert call_count == 1  # only called once, no retries
        assert mock_sleep.call_count == 0

    @pytest.mark.asyncio
    async def test_async_retry_metrics_updated(self) -> None:
        """Verify metrics dict is updated on async retry."""
        retrier = ExponentialRetry(max_retries=3, base_delay=1.0, jitter=False)
        call_count = 0
        metrics: dict = {}

        async def failing_func(**kwargs: dict) -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("transient error")
            return "success"

        await retrier.retry_async(func=failing_func, input_args={"metrics": metrics})

        assert metrics["retries"] == 1
        assert metrics["requests_with_retries"] == 1

    @pytest.mark.asyncio
    async def test_async_retry_metrics_no_retries(self) -> None:
        """Verify metrics show zero retries on first async success."""
        retrier = ExponentialRetry(max_retries=3, base_delay=1.0, jitter=False)
        metrics: dict = {}

        async def success_func(**kwargs: dict) -> str:
            return "success"

        await retrier.retry_async(func=success_func, input_args={"metrics": metrics})

        assert metrics["retries"] == 0
        assert metrics["requests_with_retries"] == 0


class TestExponentialRetryJitter:
    """Tests for jitter behavior in retry delays."""

    def test_sync_retry_with_jitter_adds_randomness(self) -> None:
        """Verify sync retry with jitter produces delays in expected range."""
        retrier = ExponentialRetry(max_retries=5, base_delay=1.0, jitter=True)
        call_count = 0

        def always_fail(**kwargs: dict) -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("persistent error")

        with patch("time.sleep") as mock_sleep:
            with pytest.raises(ValueError, match="persistent error"):
                retrier.retry(func=always_fail, input_args={})

        actual_calls = [call[0][0] for call in mock_sleep.call_args_list]
        # With base_delay=1.0 and jitter=True:
        # delay starts at 1.0, stays 1.0 after *=base_delay
        # sleep_delay = 1.0 + uniform(0, 1) → range [1.0, 2.0)
        for actual in actual_calls:
            assert 1.0 <= actual < 2.0, f"Delay {actual} out of expected range [1.0, 2.0)"

    @pytest.mark.asyncio
    async def test_async_retry_with_jitter_adds_randomness(self) -> None:
        """Verify async retry with jitter produces delays in expected range."""
        retrier = ExponentialRetry(max_retries=5, base_delay=1.0, jitter=True)
        call_count = 0

        async def always_fail(**kwargs: dict) -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("persistent error")

        with patch("asyncio.sleep") as mock_sleep:
            with pytest.raises(ValueError, match="persistent error"):
                await retrier.retry_async(func=always_fail, input_args={})

        actual_calls = [call[0][0] for call in mock_sleep.call_args_list]
        for actual in actual_calls:
            assert 1.0 <= actual < 2.0, f"Delay {actual} out of expected range [1.0, 2.0)"
