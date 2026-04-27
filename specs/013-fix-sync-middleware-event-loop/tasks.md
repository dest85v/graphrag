# Tasks: Fix sync middleware event loop crashes

**Input**: Design documents from `/specs/013-fix-sync-middleware-event-loop/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: REQUIRED per Constitution Principle III (Test-First, NON-NEGOTIABLE). All tests written before implementation.

**Organization**: Tasks organized by user story (both P1, independently testable).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Maps to user story from spec.md (US1, US2)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Ensure test infrastructure and dependency availability

- [ ] T001 Verify `anyio` is available in `graphrag-llm` dependency resolution via `uv run python -c "import anyio; print(anyio.__version__)"`
- [ ] T002 [P] Back up current test baseline: run `uv run poe test_unit -- -k "mcp or middleware"` and capture results for regression comparison

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core helper and test scaffolding that MUST be complete before ANY user story.

**⚠️ CRITICAL**: No user story implementation can begin until this phase is complete.

### Tests for Foundational (written first, must FAIL)

- [ ] T003 [P] [US1] Unit test for `RuntimeError` crash — call `MCPMiddleware._wrap_completion()` from async context in `tests/unit/mcp/test_middleware.py::TestMCPAsyncContextSyncCall::test_sync_from_async_context_no_crash`
- [ ] T004 [P] [US1] Unit test for `asyncio.run()` replacement — verify `_run_async_in_loop()` helper reuses running loop in `tests/unit/mcp/test_middleware.py::TestMCPAsyncContextSyncCall::test_sync_uses_running_loop`
- [ ] T005 [P] [US2] Unit test for event loop leak — 100 sequential cache calls via `tests/unit/middleware/test_with_cache_sync_event_loop.py::test_no_event_loop_leak_under_load`
- [ ] T006 [P] [US2] Unit test for `_run_async_in_loop` from sync entry point — verify it creates and closes a new loop in `tests/unit/middleware/test_with_cache_sync_event_loop.py::test_sync_entry_point_creates_new_loop`

### Implementation for Foundational

- [ ] T007 Create `_run_async_in_loop()` helper in `packages/graphrag-llm/graphrag_llm/middleware/_event_loop.py` with: try/except `asyncio.get_running_loop()`, `anyio.from_thread.run()` when running, `new_event_loop()` + `run_until_complete()` + `close()` when not running
- [ ] T008 Implement test for T003: write failing test that calls `MCPMiddleware._wrap_completion()` from `asyncio.run()` context, expecting `RuntimeError` to NOT be raised
- [ ] T009 Implement test for T004: write failing test that asserts `anyio.from_thread.run()` is called (patched/mock) when inside an async context
- [ ] T010 Implement test for T005: write failing test that calls sync cache middleware 100 times and asserts `len([o for o in gc.get_objects() if isinstance(o, asyncio.AbstractEventLoop)])` stays stable
- [ ] T011 Implement test for T006: write failing test that calls the helper from a sync context and verifies a new loop is created and closed

**Checkpoint**: Foundation ready — all tests written and failing. Implementation begins below.

- [ ] T012 Replace `asyncio.run()` in `packages/graphrag-llm/graphrag_llm/mcp/middleware.py:414` with `_run_async_in_loop()` helper — make tools importable, import from `._event_loop`
- [ ] T013 Replace `asyncio.new_event_loop()` / `event_loop.run_until_complete()` pattern in `packages/graphrag-llm/graphrag_llm/middleware/with_cache.py:69-103` with `_run_async_in_loop()` helper — import from `._event_loop`
- [ ] T014 Fix exception handling in `packages/graphrag-llm/graphrag_llm/mcp/middleware.py:302-303` — replace bare `except Exception:` with `except Exception as e: log.exception(...)` for tool call detection
- [ ] T015 Fix exception handling in `packages/graphrag-llm/graphrag_llm/mcp/middleware.py:384-385` — same pattern for sync path tool call detection
- [ ] T016 Fix exception handling in `packages/graphrag-llm/graphrag_llm/middleware/with_cache.py:92-95` — replace bare `except Exception:` with `except Exception as e: log.exception(...)` for cache read
- [ ] T017 Fix exception handling in `packages/graphrag-llm/graphrag_llm/middleware/with_cache.py:140-143` — same pattern for async cache read

**Checkpoint**: Foundational implementation complete. All 4 foundational tests must now PASS.

---

## Phase 3: User Story 1 - LLM calls with MCP tools work from any context (Priority: P1) 🎯 MVP

**Goal**: `MCPMiddleware._wrap_completion()` must work when called from an async context (no `RuntimeError: This event loop is already running`).

**Independent Test**: Call `MCPMiddleware._wrap_completion()` from within a running async context with mocked LLM returning tool calls. Verify no `RuntimeError`, verify `call_tool()` is invoked via `_run_async_in_loop()`, verify response is returned.

### Additional Tests for User Story 1

- [ ] T018 [US1] Integration test: `MCPMiddleware` sync path with mocked MCP client, called from async context, in `tests/integration/mcp/test_middleware_tool_call.py::TestMCPFromAsyncContext::test_sync_completion_from_async_context_with_tool_calls`
- [ ] T019 [US1] Integration test: `MCPMiddleware` sync path with tool call error handling from async context, in `tests/integration/mcp/test_middleware_tool_call.py::TestMCPFromAsyncContext::test_sync_tool_call_error_from_async_context`

### Additional Implementation for User Story 1

- [ ] T020 [US1] Integration test T018: full integration test — mock `MCPClient.call_tool` as async, call `_wrap_completion()` from `asyncio.run()`, verify tool calls are executed and response returned correctly
- [ ] T021 [US1] Integration test T019: integration test — mock `MCPClient.call_tool` to raise, verify error is handled gracefully and caught in async context

**Checkpoint**: User Story 1 fully functional. All US1 tests (T003, T004, T018, T019) must PASS.

---

## Phase 4: User Story 2 - Cache middleware does not leak event loops (Priority: P1)

**Goal**: Cache middleware must not create a new event loop per invocation. No loop accumulation. Async variant reuses existing loop.

**Independent Test**: Make 100 sequential sync cache middleware calls. Verify event loop object count remains stable (±0). Verify sync cache hit/miss paths both work correctly. Verify async variant works identically.

### Additional Tests for User Story 2

- [ ] T022 [US2] Benchmark test: sync cache middleware latency per call <50ms overhead in `tests/unit/middleware/test_with_cache_sync_event_loop.py::test_sync_cache_latency_benchmark`
- [ ] T023 [US2] Unit test: async cache middleware reuses existing loop (no new loop created) in `tests/unit/middleware/test_with_cache_sync_event_loop.py::test_async_cache_reuses_running_loop`
- [ ] T024 [US2] Integration test: cache middleware sync+async paths produce identical results in `tests/integration/mcp/test_middleware_tool_call.py` or dedicated integration file

### Additional Implementation for User Story 2

- [ ] T025 [US2] Benchmark test T022: measure wall-clock time for 100 sync cache misses, verify total < 5 seconds (avg <50ms/call overhead for cache ops)
- [ ] T026 [US2] Async cache test T023: verify that `_cache_middleware_async` uses `await` directly (no loop creation) — patch `asyncio.new_event_loop` and assert it was never called

**Checkpoint**: User Story 2 fully functional. All US2 tests (T005, T006, T010, T011, T022, T023, T024) must PASS.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Ensure quality, backward compatibility, and zero regression.

- [ ] T027 Run full existing test suite: `uv run poe test_unit -- -k "mcp or middleware"` and `uv run poe test_integration -- -k "mcp"` — all existing tests must pass (SC-004)
- [ ] T028 [P] Run full CI check: `uv run poe check` — format + lint + typecheck must pass
- [ ] T029 [P] Run full test suite: `uv run poe test` — no regressions in other packages
- [ ] T030 Update `quickstart.md` verification results with actual test output
- [ ] T031 Add semversioner change entry: `uv run semversioner add-change -t patch -d "Fix asyncio.run() crash in sync middleware when called from async context, and eliminate event loop leak in cache middleware."`
- [ ] T032 Verify backward compatibility: test `MCPMiddleware._wrap_completion()` from pure sync context (no running loop) — must still work with `new_event_loop()` fallback

**Checkpoint**: All tests pass, CI clean, backward compatibility confirmed. Feature ready for PR.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Stories (Phase 3-4)**: Both P1, can run in parallel after Foundational
- **Polish (Phase 5)**: Depends on both US1 and US2 completion

### User Story Dependencies

- **US1 (P1)**: After Foundational — focuses on MCP middleware sync→async bridging
- **US2 (P1)**: After Foundational — focuses on cache middleware loop elimination
- US1 and US2 are independently testable (different files: `mcp/middleware.py` vs `middleware/with_cache.py`)

### Within Each Phase

- Tests MUST be written and FAIL before implementation (Constitution Principle III)
- Foundational helper (T007) must exist before tests that depend on it (T003-T006)
- Tests (T008-T011) must fail before implementation (T012-T017)

### Parallel Opportunities

- T001, T002 (Setup) — parallel
- T003-T006 (Foundational tests) — parallel (different files)
- T018, T019 (US1 integration tests) — parallel
- T022-T024 (US2 tests) — parallel
- T027-T029 (Polish) — parallel

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (helper + foundational tests)
3. Complete Phase 3: US1 (MCP middleware fix)
4. **STOP and VALIDATE**: Run US1 tests independently
5. Demo: sync MCP middleware works from async context

### Incremental Delivery

1. Setup + Foundational → shared helper ready
2. US1 → MCP middleware fix verified
3. US2 → Cache middleware fix verified
4. Polish → full suite + backward compatibility

---

## Notes

- **Constitution Principle III (Test-First) is NON-NEGOTIABLE**: All tests MUST be written and FAIL before implementation code.
- **anyio is already available** as a transitive dependency via `openai` SDK — verify in T001.
- Both US1 and US2 are P1 priority and independently testable — can be worked on in parallel.
- The `_run_async_in_loop()` helper is the only new code artifact — minimal, well-tested, shared by both middlewares.
- No public API changes — all changes are internal behavior fixes. Existing callers see no behavioral change.
