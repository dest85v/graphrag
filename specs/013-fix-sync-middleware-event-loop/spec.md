# Feature Specification: Fix sync middleware event loop crashes

**Feature Branch**: `013-fix-sync-middleware-event-loop`  
**Created**: 2026-04-26  
**Status**: Draft  
**Input**: User description: "P1 — Исправить `asyncio.run()` / event loop в sync middleware"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - LLM calls with MCP tools work from any context (Priority: P1)

Users invoke the LLM completion API through `MCPMiddleware` (which wraps an MCP tool-calling client). Currently, when the middleware's sync wrapper is called from within an already-running async context (e.g., inside an async FastAPI endpoint or any async pipeline), it crashes with `RuntimeError: This event loop is already running` because `asyncio.run()` cannot nest inside a running event loop.

**Why this priority**: This is a hard crash that makes the MCP middleware unusable in any async application context. All users who enable MCP tool-calling from async code will hit this.

**Independent Test**: Call `MCPMiddleware.complete_sync()` from within a running async context (e.g., from an async function, or from inside `asyncio.run()`'s loop). Verify the call completes without crashing, and MCP tool calls execute correctly.

**Acceptance Scenarios**:

1. **Given** MCP middleware is configured with tools, **When** `complete_sync()` is called from an async context, **Then** the call returns a valid response without `RuntimeError`
2. **Given** MCP middleware is configured with tools, **When** `complete_sync()` is called from a truly sync context (no running event loop), **Then** the call returns a valid response (backward compatibility preserved)
3. **Given** the LLM responds with tool calls, **When** the middleware executes them via `call_tool()`, **Then** tool results are correctly fed back into the conversation and the response is returned

---

### User Story 2 - Cache middleware does not leak event loops (Priority: P1)

Users rely on `with_cache` middleware to reduce LLM API costs via response caching. The sync variant creates a brand new event loop on every cache lookup/write. This is extremely expensive under load: each cache miss spawns a new loop, does one async operation, then tears it down. High-throughput applications see massive GC pressure and degraded performance.

**Why this priority**: Even if not crashing, this causes severe performance degradation under load. Every cache miss in a sync call path wastes CPU cycles and memory.

**Independent Test**: Make 100 sequential cache misses via the sync cache middleware. Verify no event loop objects accumulate in memory, and response latency per call stays below a reasonable threshold (e.g., <50ms overhead for cache ops).

**Acceptance Scenarios**:

1. **Given** cache middleware is active, **When** multiple sync calls trigger cache lookups, **Then** no event loop objects accumulate (verified by memory profiling)
2. **Given** the async variant of cache middleware, **When** cache lookups happen, **Then** they use the existing running event loop (no new loop created)
3. **Given** both sync and async cache middleware, **When** called under high throughput, **Then** cache hit/miss latency remains consistent

---

### Edge Cases

- What happens when `anyio.from_thread.run()` is called from a thread that already has a running event loop in a different loop policy (e.g., `curio` or `trio`)? → Falls back to detecting running loop via `asyncio.get_event_loop_policy().get_event_loop()` with `RuntimeError` catch.
- What happens if the MCP client initialization fails inside the new async context? → Exception propagates to the sync caller with full traceback.
- What happens if cache backend requires a specific event loop (e.g., uvloop-specific behavior)? → Uses `anyio` abstraction which is loop-agnostic.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: MCP middleware sync wrapper MUST detect if an event loop is already running and reuse it instead of calling `asyncio.run()`
- **FR-002**: MCP middleware sync wrapper MUST create a new isolated event loop only when no loop is currently running (true sync entry point)
- **FR-003**: Cache middleware sync wrapper MUST NOT create a new event loop per invocation; it MUST use an existing running loop or `anyio.from_thread.run()`
- **FR-004**: Cache middleware async wrapper MUST reuse the existing running event loop (no loop creation)
- **FR-005**: Both middlewares MUST maintain backward compatibility — existing callers that invoke sync methods from pure sync contexts must see no behavioral change
- **FR-006**: All existing `asyncio.run()` and `asyncio.new_event_loop()` calls in MCP middleware and cache middleware MUST be replaced with loop-aware alternatives
- **FR-007**: Exception handling in both middlewares MUST log errors with `exc_info=True` instead of silently swallowing (related P1 silent exception issue)

### Key Entities

- **MCPMiddleware**: The sync wrapper layer around MCP tool-calling client. Responsible for initializing the MCP client and executing tool calls in response to LLM tool_call tokens.
- **WithCache middleware factory**: Factory function that produces sync and async cache-wrapping middleware pairs. Responsible for checking cache before/after LLM calls.
- **Event loop lifecycle**: The pattern of loop creation, execution, and teardown. Currently broken in sync paths; target pattern is "reuse or create-at-entry-point only."

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of sync middleware calls from an async context complete without `RuntimeError` (verified by unit test)
- **SC-002**: Event loop object count remains stable (±0 new loops) after 1000 sequential sync cache calls (verified by memory profiler)
- **SC-003**: Sync cache middleware adds <50ms overhead per call for cache operations (verified by benchmark)
- **SC-004**: All existing unit and integration tests for `MCPMiddleware` and `with_cache` pass without modification (zero regression)

## Assumptions

- `anyio` is already available as a transitive dependency (used by `openai` SDK); if not, it will be added as an optional or direct dependency
- The MCP client's `call_tool()` is an async function that works correctly when called via `anyio.from_thread.run()` or on an existing event loop
- Cache backends (`graphrag-cache`) support being called from any event loop via `anyio`'s loop-agnostic abstraction
- Python 3.11+ `asyncio` APIs (`get_running_loop`, `new_event_loop`) are used for detection; no Python version downgrades
- The fix is scoped to `graphrag-llm` package only (MCP middleware + cache middleware); no changes to other packages
