# Implementation Plan: Fix sync middleware event loop crashes

**Branch**: `013-fix-sync-middleware-event-loop` | **Date**: 2026-04-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/013-fix-sync-middleware-event-loop/spec.md`

## Summary

Fix `asyncio.run()` crashes and event loop leaks in two sync middleware components within `graphrag-llm`:
1. `MCPMiddleware._wrap_completion()` uses `asyncio.run()` for tool calls (line 414) — crashes when called from an async context with a `RuntimeError: This event loop is already running`.
2. `with_cache` middleware sync wrapper creates a new event loop per invocation (lines 69-103) — causes severe GC pressure under load.

Solution: Detect running event loop at sync entry points; if one exists, use `anyio.from_thread.run()` or inject the loop directly; otherwise create a new loop.

## Technical Context

**Language/Version**: Python 3.11+ (workspace `requires-python = ">=3.11,<3.14"`)  
**Primary Dependencies**: `anyio` (transitive via `openai` SDK), `openai~=1.60`, `pydantic`  
**Storage**: N/A (runtime middleware only, no persistence)  
**Testing**: `pytest` with `asyncio_mode = "auto"`, suites: `unit`, `integration`, `smoke`, `notebook`, `verbs`  
**Target Platform**: Linux/Unix servers, any Python 3.11-3.13 environment  
**Project Type**: Library (middleware layer in monorepo)  
**Performance Goals**: Sync cache middleware adds <50ms overhead per call; zero event loop leaks under load  
**Constraints**: Must maintain backward compatibility — pure sync callers see no behavioral change; scoped to `graphrag-llm` package only  
**Scale/Scope**: 2 files in `graphrag-llm`: `mcp/middleware.py`, `middleware/with_cache.py`; existing tests in `tests/unit/mcp/`, `tests/integration/mcp/`

## Constitution Check

**GATE**: Must pass before Phase 0 research. Re-check after Phase 1 design.

| Principle | Compliance | Notes |
|-----------|------------|-------|
| **I. Library-First** | ✅ PASS | Fix is scoped to `graphrag-llm` package only. No new libraries introduced. |
| **II. CLI Interface** | ✅ PASS | No CLI changes; middleware is internal. |
| **III. Test-First** | ✅ PASS | New tests will be written before implementation (per constitution). Unit + integration tests for both middlewares. |
| **IV. Integration Testing** | ✅ PASS | Integration tests exist (`tests/integration/mcp/test_middleware_tool_call.py`); will add integration test for async-context sync call. |
| **V. Versioning** | ✅ PASS | semversioner change entry required before merge (`patch` — internal bug fix). |

**Post-Phase 1 re-check** (to be completed after design):
- Same gates — no architectural changes that would affect constitution compliance.

## Project Structure

### Documentation (this feature)

```text
specs/013-fix-sync-middleware-event-loop/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (minimal — middleware fix)
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (no public API changes)
└── tasks.md             # Phase 2 output
```

### Source Code (repository)

```text
packages/graphrag-llm/graphrag_llm/
├── mcp/middleware.py          # ← MCPMiddleware._wrap_completion() needs fix (asyncio.run → loop-aware)
├── middleware/with_cache.py   # ← with_cache sync wrapper needs fix (new_event_loop → anyio.from_thread)
tests/unit/mcp/test_middleware.py  # ← Existing MCP middleware tests; new tests for async-context sync calls
tests/integration/mcp/test_middleware_tool_call.py  # ← Existing integration tests
```

**Structure Decision**: No new files needed for the fix. All changes are within existing files in `graphrag-llm`. New tests will be added to existing test files. No new packages or dependencies beyond `anyio` (already a transitive dependency).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Introducing `anyio.from_thread.run()` | Must bridge sync→async from an already-running event loop | `asyncio.run()` crashes; `asyncio.get_event_loop()` with `set_event_loop()` is deprecated in Python 3.10+ and doesn't solve the nested-loop problem |
| Event loop injection helper | Shared pattern used by both middlewares | Duplication across 2 files violates DRY; a small internal utility keeps code maintainable |
