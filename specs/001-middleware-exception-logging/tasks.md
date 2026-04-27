---

description: "Task list for fixing silent exception swallowing in middleware"
---

# Tasks: Fix Middleware Exception Logging

**Input**: Design documents from `/specs/001-middleware-exception-logging/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Only test tasks for the new cache write exception handling (US1). MCP and search files already have adequate tests for existing logging.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Feature branch and artifact setup — already done by `/speckit.specify` and `/speckit.plan`

- [x] T001 Verify feature branch `001-middleware-exception-logging` exists and is clean

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Understand the existing exception handling landscape

- [x] T002 Audit all `except Exception` blocks in `with_cache.py`, `mcp/middleware.py`, and `search.py` — map each block to whether it logs, continues, or re-raises

**Checkpoint**: Foundation ready — all exception handling gaps identified in `research.md`. User story implementation can begin.

---

## Phase 3: User Story 1 - Developer debugging failed cache operations (Priority: P1)

**Goal**: Wrap `cache.set()` calls in `with_cache.py` with try/except + warning logging so cache write failures are observable without breaking the response.

**Independent Test**: Simulate a cache server that rejects writes. Verify that `log.warning()` is emitted and the LLM response is still returned correctly.

### Implementation for User Story 1

- [x] T003 [P] [US1] Wrap sync `cache.set()` in `_cache_middleware` with try/except + `log.exception()` in `packages/graphrag-llm/graphrag_llm/middleware/with_cache.py:102`
- [x] T004 [P] [US1] Wrap async `await cache.set()` in `_cache_middleware_async` with try/except + `log.exception()` in `packages/graphrag-llm/graphrag_llm/middleware/with_cache.py:147`
- [x] T005 [US1] Add unit test for cache write failure logging in `tests/unit/middleware/test_cache_write_failure_logging.py`

**Checkpoint**: US1 is independently testable — cache write failures now produce observable log warnings.

---

## Phase 4: User Story 2 - Developer debugging MCP tool call failures (Priority: P1)

**Goal**: Add logging to all broad `except Exception` blocks in MCP middleware and make sync/async paths consistent (both track exceptions).

**Independent Test**: Configure MCP middleware with a tool that raises an unexpected exception. Verify both sync and async paths log the error AND include it in the exceptions list.

### Implementation for User Story 2

- [x] T006 [P] [US2] Add `log.exception()` call to async `except Exception` block in `_execute_tool_calls` in `packages/graphrag-llm/graphrag_llm/mcp/middleware.py:245-247`
- [x] T007 [US2] Add `log.exception()` call AND add exception to `exceptions` list to sync unexpected-except block in `_wrap_completion` in `packages/graphrag-llm/graphrag_llm/mcp/middleware.py:426-427`
- [x] T008 [US2] Add unit test for MCP unexpected exception logging in `tests/unit/mcp/test_middleware_exception_logging.py`

**Checkpoint**: US2 is independently testable — all MCP tool call exceptions are now logged and tracked.

---

## Phase 5: User Story 3 - Developer debugging global search failures (Priority: P2)

**Goal**: Verify `search.py` already logs exceptions properly and confirm no changes needed.

**Independent Test**: Simulate a map or reduce response failure. Verify `logger.exception()` is called and fallback SearchResult is returned.

### Verification for User Story 3

- [x] T009 [US3] Verify `logger.exception()` is called in `_map_response_single_batch` exception handler in `packages/graphrag/graphrag/query/structured_search/global_search/search.py:267`
- [x] T010 [US3] Verify `logger.exception()` is called in `_reduce_response` exception handler in `packages/graphrag/graphrag/query/structured_search/global_search/search.py:424`

**Checkpoint**: US3 verified — no code changes needed, existing logging is adequate.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finalize, validate, and prepare for merge

- [x] T011 [P] Run `uv run poe check` on modified files — confirm 0 lint/type errors
- [x] T012 [P] Run `uv run poe test` — confirm all existing tests pass (zero regression, SC-004)
- [x] T013 [US1+US2+US3] Verify SC-001 (100% exceptions logged), SC-002 (zero silent swallowing), SC-003 (consistent sync/async)
- [x] T014 Add semversioner PATCH change entry

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational completion
  - US1 and US2 can be done in parallel (different files, different middleware)
  - US3 can start anytime after Phase 2 (verification only)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Independent — only touches `with_cache.py`
- **US2 (P1)**: Independent — only touches `mcp/middleware.py`
- **US3 (P2)**: Independent — verification only, no changes needed

### Parallel Opportunities

- T003 and T004 (US1): Can run in parallel — same file but independent cache.set() locations
- T006 and T007 (US2): Can run in parallel — same file but independent exception blocks (async vs sync)
- US1 and US2 can be done in parallel by different developers
- US3 can start as soon as Phase 2 completes

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational audit
3. Complete Phase 3: US1 (cache write logging) — independently testable
4. Complete Phase 4: US2 (MCP logging consistency) — independently testable
5. **STOP and VALIDATE**: Run `poe check` + `poe test`

### Incremental Delivery

1. US1 only → cache failures visible (biggest impact — affects all LLM callers)
2. US2 → MCP tool failures visible
3. US3 → verification confirmed, no changes
4. Polish → clean up, semversioner, merge

### Parallel Team Strategy

With multiple developers:

1. Complete Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 (with_cache.py)
   - Developer B: US2 (mcp/middleware.py)
   - Developer C: US3 (search.py — verification)
3. Stories complete independently → Polish → merge

---

## Notes

- T009-T010 (US3) are verification tasks — no code changes expected
- The `# noqa: BLE001` suppressions on broad `except Exception` blocks are kept — logging addition addresses the P1 concern without removing the lint suppression (deferred to separate lint cleanup)
- All changes are additive — no control flow changes, no API changes
- semversioner PATCH (not MINOR) because this is an internal visibility improvement with no behavioral changes
