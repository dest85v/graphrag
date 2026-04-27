# Copyright (c) 2024 Microsoft Corporation.
# Licensed under the MIT License

"""Event loop utilities for sync→async bridging.

Provides a helper to run async coroutines from synchronous code,
automatically detecting whether an event loop is already running
and reusing it via ``anyio.from_thread.run()`` instead of creating
a new loop on every call.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable

T = TypeVar("T")


def run_async_in_loop(coro: Awaitable[T]) -> T:
    """Run an async coroutine, reusing a running loop or creating one.

    When called from a synchronous context that already has a running
    event loop (e.g. inside ``asyncio.run()`` or a FastAPI handler), this
    bridges into the existing loop via ``anyio.from_thread.run()``,
    avoiding the ``RuntimeError`` that ``asyncio.run()`` raises in that
    situation.

    When no loop is running (true sync entry point), a new isolated loop
    is created, used, and closed — matching the previous ``new_event_loop()``
    pattern.

    Parameters
    ----------
    coro : Awaitable[T]
        The async coroutine to execute.

    Returns
    -------
    T
        The result of the coroutine.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No loop is running — create an isolated one.
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    # A loop is already running — bridge into it.
    import anyio

    return anyio.from_thread.run(coro)  # type: ignore[no-any-return]
