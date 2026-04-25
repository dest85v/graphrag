# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

import pandas as pd
import pytest
from graphrag.config.enums import AsyncType
from graphrag.index.utils.derive_from_rows import (
    ParallelizationError,
    derive_from_rows,
)

pytestmark = pytest.mark.asyncio


async def test_derive_from_rows_all_success():
    """All rows succeed — returns full result list."""
    df = pd.DataFrame({"value": [1, 2, 3, 4, 5]})

    async def identity(row):
        return row["value"] * 2

    result = await derive_from_rows(
        df, identity, async_type=AsyncType.AsyncIO, progress_msg="test",
    )

    assert result == [2, 4, 6, 8, 10]


async def test_derive_from_rows_continue_on_error_returns_partial():
    """10% errors with continue_on_error=True — returns partial result, does not raise."""
    errors_seen = []

    async def flaky_transform(row):
        val = row["value"]
        if val % 5 == 0:
            errors_seen.append(val)
            raise ValueError(f"simulated failure on {val}")
        return val * 2

    df = pd.DataFrame({"value": list(range(1, 11))})  # 1-10, 5 and 10 fail (div by 5)
    result = await derive_from_rows(
        df,
        flaky_transform,
        async_type=AsyncType.AsyncIO,
        progress_msg="test",
        continue_on_error=True,
    )

    # 5 and 10 should be None (errors), all others should be doubled
    assert len(result) == 10
    assert result[4] is None  # value=5
    assert result[9] is None  # value=10
    assert result[0] == 2
    assert result[1] == 4
    assert result[2] == 6
    assert result[3] == 8
    assert result[5] == 12


async def test_derive_from_rows_continue_on_error_false_raises():
    """continue_on_error=False — raises ParallelizationError on any error."""
    df = pd.DataFrame({"value": [1, 2, 3]})

    async def always_fail(row):
        raise ValueError("always fails")

    with pytest.raises(ParallelizationError) as exc_info:
        await derive_from_rows(
            df,
            always_fail,
            async_type=AsyncType.AsyncIO,
            progress_msg="test",
            continue_on_error=False,
        )

    assert "3 Errors occurred" in str(exc_info.value)
    assert exc_info.value.continue_on_error is False


async def test_derive_from_rows_mixed_success_error_continue_false():
    """Some succeed, some fail, continue_on_error=False — raises error."""
    async def mixed_transform(row):
        if row["value"] == 3:
            raise ValueError("third row fails")
        return row["value"] * 2

    df = pd.DataFrame({"value": [1, 2, 3, 4]})

    with pytest.raises(ParallelizationError) as exc_info:
        await derive_from_rows(
            df,
            mixed_transform,
            async_type=AsyncType.AsyncIO,
            progress_msg="test",
            continue_on_error=False,
        )

    assert "1 Errors occurred" in str(exc_info.value)
    # Result should be partial (2, 4, None, 8) but error is raised
    assert exc_info.value.continue_on_error is False


async def test_derive_from_rows_empty_dataframe():
    """Empty dataframe — returns empty list."""
    df = pd.DataFrame({"value": []})

    async def identity(row):
        return row["value"]

    result = await derive_from_rows(
        df, identity, async_type=AsyncType.AsyncIO, progress_msg="test",
    )

    assert result == []


async def test_derive_from_rows_all_errors_continue_on_error_true():
    """All rows fail with continue_on_error=True — returns all None, no exception."""
    async def always_fail(row):
        raise ValueError("always fails")

    df = pd.DataFrame({"value": [1, 2, 3]})
    result = await derive_from_rows(
        df,
        always_fail,
        async_type=AsyncType.AsyncIO,
        progress_msg="test",
        continue_on_error=True,
    )

    assert result == [None, None, None]


async def test_derive_from_rows_threads_continue_on_error():
    """Thread-based async type with continue_on_error=True."""
    async def flaky_transform(row):
        val = row["value"]
        if val % 3 == 0:
            raise ValueError(f"failure on {val}")
        return val * 2

    df = pd.DataFrame({"value": list(range(1, 7))})  # 1-6, 3 and 6 fail
    result = await derive_from_rows(
        df,
        flaky_transform,
        async_type=AsyncType.Threaded,
        progress_msg="test",
        continue_on_error=True,
    )

    assert len(result) == 6
    assert result[2] is None  # value=3
    assert result[5] is None  # value=6
    assert result[0] == 2
    assert result[1] == 4


async def test_derive_from_rows_single_error():
    """Single error — continue_on_error=True returns partial, False raises."""
    async def single_fail(row):
        if row["value"] == 3:
            raise ValueError("only third fails")
        return row["value"] * 2

    df = pd.DataFrame({"value": [1, 2, 3, 4, 5]})

    # With continue_on_error=True
    result = await derive_from_rows(
        df,
        single_fail,
        async_type=AsyncType.AsyncIO,
        progress_msg="test",
        continue_on_error=True,
    )

    assert result[2] is None
    assert result[0] == 2
    assert result[4] == 10

    # With continue_on_error=False
    with pytest.raises(ParallelizationError):
        await derive_from_rows(
            df,
            single_fail,
            async_type=AsyncType.AsyncIO,
            progress_msg="test",
            continue_on_error=False,
        )


async def test_parallelization_error_message():
    """ParallelizationError includes error count and example message."""
    error = ParallelizationError(3, "first error message", continue_on_error=False)
    msg = str(error)

    assert "3 Errors occurred" in msg
    assert "first error message" in msg
    assert error.continue_on_error is False


async def test_parallelization_error_no_example():
    """ParallelizationError without example message."""
    error = ParallelizationError(1)
    msg = str(error)

    assert "1 Errors occurred" in msg
    assert error.continue_on_error is False


async def test_derive_from_rows_default_continue_on_error_is_true():
    """Default continue_on_error behavior — should not raise on errors."""
    async def fail_on_odd(row):
        if row["value"] % 2 == 1:
            raise ValueError("odd value")
        return row["value"]

    df = pd.DataFrame({"value": [1, 2, 3, 4]})

    # Should NOT raise because default is continue_on_error=True
    result = await derive_from_rows(
        df, fail_on_odd, async_type=AsyncType.AsyncIO, progress_msg="test",
    )

    assert result[0] is None  # value=1
    assert result[1] == 2     # value=2
    assert result[2] is None  # value=3
    assert result[3] == 4     # value=4
