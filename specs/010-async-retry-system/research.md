# Research: Async Non-Blocking Retry Sleep

**Feature**: 010-async-retry-system  
**Date**: 2026-04-25

## Decision: No code changes needed — focus on test coverage

The `time.sleep()` in `ExponentialRetry.retry_async()` identified by the P0 task review was already fixed in the upstream V3/main branch (commit `4c8ef97` and later). The async path at line 115 of `exponential_retry.py` uses `await asyncio.sleep(sleep_delay)`.

## Verification Details

### All retry-related `time.sleep()` calls audited:

1. **`exponential_retry.py:84`** — `time.sleep()` in `retry()` (sync path) — **CORRECT**. Sync path should block.
2. **`exponential_retry.py:115`** — `await asyncio.sleep()` in `retry_async()` (async path) — **CORRECT**. Already async-aware.
3. **`with_errors_for_testing.py:61`** — `time.sleep()` in sync test middleware — **CORRECT**. Sync path.
4. **`with_errors_for_testing.py:74`** — `await asyncio.sleep()` in async test middleware — **CORRECT**.
5. **`sliding_window_rate_limiter.py:135`** — `time.sleep()` in `SlidingWindowRateLimiter.acquire()` — **ACCEPTABLE**. This is inside a `threading.Lock` context, which is a synchronous concurrency primitive. The rate limiter is inherently synchronous (thread-level), not async. No fix needed.

### `ImmediateRetry` has no sleep:
Both `retry()` and `retry_async()` in `immediate_retry.py` have no backoff delay — they retry immediately. No sleep calls to audit.

## Best Practices for Async Sleep

### Python asyncio sleep patterns:

1. **Always use `await asyncio.sleep()` in async functions** — never mix `time.sleep()` in async context.
2. **`time.sleep()` is correct in sync functions** — blocking the calling thread is expected behavior.
3. **`asyncio.sleep(0)` is a yield point** — yields control to the event loop without actual delay. Useful for cooperative multitasking.
4. **`asyncio.CancelledError` during sleep** — `asyncio.sleep()` properly raises `CancelledError` when the task is cancelled, allowing clean cancellation. `time.sleep()` does not respond to cancellation.

### Test patterns:

1. **Mock `asyncio.sleep`** — verify it's called with the correct delay value.
2. **Concurrent execution timing** — spawn multiple coroutines, measure wall-clock time vs. sequential time.
3. **Mock `time.sleep`** — verify sync path still blocks as expected.

## Alternatives Considered

1. **Patch existing code** — rejected, code is already correct.
2. **Add a `@non_blocking_retry` decorator** — unnecessary complexity, existing `Retry` ABC already provides the interface.
3. **Use `asyncio.to_thread()` for sync retry** — over-engineered, `time.sleep()` in sync context is idiomatic.

## Dependencies

- No new dependencies required
- Existing: `pytest`, `pytest-asyncio`, `unittest.mock` (stdlib)
