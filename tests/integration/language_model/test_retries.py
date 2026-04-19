# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Test OpenAI SDK Retries."""

import time
from collections.abc import Callable
from typing import Any

import httpx
import openai
import pytest
from graphrag_llm.config import RetryConfig, RetryType
from graphrag_llm.retry import create_retry


@pytest.mark.parametrize(
    ("config", "max_retries", "expected_time"),
    [
        (
            RetryConfig(
                type=RetryType.ExponentialBackoff,
                max_retries=3,
                base_delay=2.0,
                jitter=False,
            ),
            3,
            2 + 4 + 8,  # No jitter, so exact times
        ),
        (
            RetryConfig(
                type=RetryType.Immediate,
                max_retries=3,
            ),
            3,
            0,  # Immediate retry, so no delay
        ),
    ],
)
def test_retries(config: RetryConfig, max_retries: int, expected_time: float) -> None:
    """
    Test various retry strategies with various configurations.
    """
    retry_service = create_retry(config)

    # start at -1 because the first call is not a retry
    retries = -1

    def mock_func():
        nonlocal retries
        retries += 1
        msg = "Mock error for testing retries"
        raise ValueError(msg)

    start_time = time.time()
    with pytest.raises(ValueError, match="Mock error for testing retries"):
        retry_service.retry(func=mock_func, input_args={})
    elapsed_time = time.time() - start_time

    assert retries == max_retries, f"Expected {max_retries} retries, got {retries}"
    assert elapsed_time >= expected_time, (
        f"Expected elapsed time >= {expected_time}, got {elapsed_time}"
    )


@pytest.mark.parametrize(
    ("config", "max_retries", "expected_time"),
    [
        (
            RetryConfig(
                type=RetryType.ExponentialBackoff,
                max_retries=3,
                base_delay=2.0,
                jitter=False,
            ),
            3,
            2 + 4 + 8,  # No jitter, so exact times
        ),
        (
            RetryConfig(
                type=RetryType.Immediate,
                max_retries=3,
            ),
            3,
            0,  # Immediate retry, so no delay
        ),
    ],
)
async def test_retries_async(
    config: RetryConfig, max_retries: int, expected_time: float,
) -> None:
    """
    Test various retry strategies with various configurations.
    """
    retry_service = create_retry(config)

    # start at -1 because the first call is not a retry
    retries = -1

    def mock_func():
        nonlocal retries
        retries += 1
        msg = "Mock error for testing retries"
        raise ValueError(msg)

    start_time = time.time()
    with pytest.raises(ValueError, match="Mock error for testing retries"):
        await retry_service.retry_async(func=mock_func, input_args={})
    elapsed_time = time.time() - start_time

    assert retries == max_retries, f"Expected {max_retries} retries, got {retries}"
    assert elapsed_time >= expected_time, (
        f"Expected elapsed time >= {expected_time}, got {elapsed_time}"
    )


# OpenAI SDK exceptions that should not trigger retries
_OPENAI_RETRY_SKIP_EXCEPTIONS: list[tuple[str, Callable[..., Any]]] = [
    (
        "BadRequestError",
        lambda: openai.BadRequestError(
            "Oh no!", response=_make_response(400), body=None,
        ),
    ),
    (
        "AuthenticationError",
        lambda: openai.AuthenticationError(
            "Oh no!", response=_make_response(401), body=None,
        ),
    ),
    (
        "PermissionDeniedError",
        lambda: openai.PermissionDeniedError(
            "Oh no!", response=_make_response(403), body=None,
        ),
    ),
    (
        "NotFoundError",
        lambda: openai.NotFoundError("Oh no!", response=_make_response(404), body=None),
    ),
    (
        "UnprocessableEntityError",
        lambda: openai.UnprocessableEntityError(
            "Oh no!", response=_make_response(422), body=None,
        ),
    ),
    (
        "APIConnectionError",
        lambda: openai.APIConnectionError(
            message="Oh no!", request=httpx.Request("GET", "https://api.openai.com"),
        ),
    ),
    (
        "APIError",
        lambda: openai.APIError(
            "Oh no!", request=httpx.Request("GET", "https://api.openai.com"), body=None,
        ),
    ),
    (
        "APIResponseValidationError",
        lambda: openai.APIResponseValidationError(
            response=_make_response(500), body=None, message="Oh no!",
        ),
    ),
]


def _make_response(status_code: int) -> httpx.Response:
    """Create a mock httpx.Response for exception construction."""
    return httpx.Response(
        status_code=status_code,
        request=httpx.Request(method="GET", url="https://openai.com"),
    )


@pytest.mark.parametrize(
    "config",
    [
        (
            RetryConfig(
                type=RetryType.ExponentialBackoff,
                max_retries=3,
                base_delay=2.0,
                jitter=False,
            )
        ),
        (
            RetryConfig(
                type=RetryType.Immediate,
                max_retries=3,
            )
        ),
    ],
)
@pytest.mark.parametrize(
    ("exception", "exception_factory"),
    _OPENAI_RETRY_SKIP_EXCEPTIONS,
)
def test_exponential_backoff_skipping_exceptions(
    config: RetryConfig, exception: str, exception_factory: Callable[..., Any],
) -> None:
    """
    Test skipping retries for exceptions that should not cause a retry.
    """
    retry_service = create_retry(config)

    # start at -1 because the first call is not a retry
    retries = -1
    exception_cls = getattr(openai, exception)

    def mock_func():
        nonlocal retries
        retries += 1
        raise exception_factory()

    with pytest.raises(exception_cls, match="Oh no!"):
        retry_service.retry(func=mock_func, input_args={})

    # subtract 1 from retries because the first call is not a retry
    assert retries == 0, (
        f"Expected not to retry for '{exception}' exception. Got {retries} retries."
    )
