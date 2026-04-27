# Research: Sync middleware event loop handling

**Feature**: 013-fix-sync-middleware-event-loop  
**Date**: 2026-04-26

## Decision 1: How to bridge sync→async when an event loop is already running

**Chosen approach**: `anyio.from_thread.run(coro, timeout=...)` for sync contexts with a running loop.

**Rationale**:
- `anyio.from_thread.run()` is specifically designed to call an async function from a synchronous thread that already has a running event loop. It uses `loop.run_until_complete()` internally when a loop is already running in the current thread, avoiding the `RuntimeError` from `asyncio.run()`.
- `anyio` is already a transitive dependency (via `openai` SDK), so no new dependencies are needed.
- `anyio` is loop-agnostic — works with `asyncio`, `trio`, or other backends.

**Alternatives evaluated**:
1. **`asyncio.run_coroutine_threadsafe(coro, loop)`** — Requires explicitly passing the event loop object. More verbose, less portable. Needs manual `loop = asyncio.get_running_loop()` call before each invocation.
2. **`asyncio.get_running_loop().run_until_complete()`** — Direct but only works when a loop is guaranteed to be running. Falls back to `asyncio.run()` when no loop exists, adding complexity.
3. **`asyncio.new_event_loop()` + `set_event_loop()`** — Creates a separate loop per call (current broken pattern for cache middleware). Causes GC pressure and doesn't share state.

**Decision**: Use `anyio.from_thread.run()` as the primary bridging mechanism. For cases where no loop is running (true sync entry point), fall back to creating a new isolated loop.

## Decision 2: Event loop detection strategy

**Chosen approach**: Check `asyncio.get_running_loop()` inside a try/except; if it raises `RuntimeError`, no loop is running — create a new one.

```python
def _run_async_in_loop(coro):
    """Run an async coroutine, reusing a running loop or creating one."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    
    if loop is not None:
        return anyio.from_thread.run(coro)
    else:
        new_loop = asyncio.new_event_loop()
        try:
            return new_loop.run_until_complete(coro)
        finally:
            new_loop.close()
```

**Rationale**:
- `asyncio.get_running_loop()` is the standard, Python 3.7+ way to detect a running loop.
- When a loop IS running, `anyio.from_thread.run()` handles the bridging.
- When no loop is running, we create an isolated loop and close it after (matching the current behavior for true sync entry points).

**Edge case handling**:
- `anyio.from_thread.run()` from a thread that's not part of the event loop's thread group will work correctly — anyio detects this and schedules on the running loop.
- If `anyio` is unavailable (shouldn't happen given openai dependency), fall back to `asyncio.run_coroutine_threadsafe()`.

## Decision 3: Cache middleware — event loop reuse

**Chosen approach**: Replace the `asyncio.new_event_loop()` + `event_loop.run_until_complete()` pattern with `_run_async_in_loop()` helper.

**Before** (lines 69-103 in `with_cache.py`):
```python
event_loop = asyncio.new_event_loop()
asyncio.set_event_loop(event_loop)
cached_response = event_loop.run_until_complete(cache.get(cache_key))
...
event_loop.run_until_complete(cache.set(cache_key, cache_value))
event_loop.close()
```

**After**:
```python
cached_response = await _run_async_in_loop(cache.get(cache_key))
...
await _run_async_in_loop(cache.set(cache_key, cache_value))
```

**Rationale**: Single helper function eliminates duplicated event loop lifecycle management. No loop accumulation.

## Decision 4: Exception handling improvement (FR-007)

**Chosen approach**: Replace bare `except Exception: ...` (silent swallow) with `except Exception as e: log.exception(...)` in both middlewares.

Files affected:
- `mcp/middleware.py`: lines 302-303, 384-385
- `with_cache.py`: lines 92-95, 140-143

**Rationale**: Silent exception swallowing hides bugs. `log.exception()` includes the full traceback while still allowing the middleware to recover gracefully.
