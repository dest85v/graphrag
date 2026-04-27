# Data Model: Sync Middleware Event Loop Fix

**Feature**: 013-fix-sync-middleware-event-loop  
**Date**: 2026-04-26

## Overview

This fix does not introduce new entities or data models. All changes are behavioral — replacing event loop lifecycle management in existing middleware classes.

## Modified Components

### `MCPCompletionMiddleware._wrap_completion()` 

**File**: `packages/graphrag-llm/graphrag_llm/mcp/middleware.py`  
**Change**: `asyncio.run()` (line 414) → `_run_async_in_loop()` helper  
**No data model changes** — same method signature, same return types.

### `with_cache` sync wrapper

**File**: `packages/graphrag-llm/graphrag_llm/middleware/with_cache.py`  
**Change**: `asyncio.new_event_loop()` (lines 69-103) → `_run_async_in_loop()` helper  
**No data model changes** — same function signature, same return types.

## Internal Helper (new)

### `_run_async_in_loop()`

**File**: `packages/graphrag-llm/graphrag_llm/middleware/_event_loop.py` (new)  
**Purpose**: Shared utility to run async code from sync contexts.

```
Signature: _run_async_in_loop(coro: Awaitable[T]) -> T
Parameters:
  coro: An awaitable coroutine to execute
Returns:
  The result of the coroutine
Behavior:
  - If a loop is already running in the current thread: uses anyio.from_thread.run(coro)
  - If no loop is running: creates a new loop, runs the coroutine, closes the loop
```

No database entities, no persisted state changes. This is purely behavioral middleware logic.
