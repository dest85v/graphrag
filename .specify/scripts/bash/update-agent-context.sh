# Implementation Plan: Async Non-Blocking Retry Sleep

**Branch**: `010-async-retry-system` | **Date**: 2026-04-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/010-async-retry-system/spec.md`

## Summary

The GraphRAG `graphrag-llm` package contains a retry middleware that wraps LLM completion and embedding calls with exponential backoff. The P0 task flagged `time.sleep()` in the retry layer as blocking the event loop.

Investigation confirms the code is **already correct** in the upstream V3/main branch: `ExponentialRetry.retry_async()` uses `await asyncio.sleep()` (line 115), and `ExponentialRetry.retry()` uses `time.sleep()` for the synchronous path (line 84). The `with_retries` middleware correctly routes sync→sync and async→async.

This plan shifts from "code fix" to **verification + test coverage**: add unit tests that assert the sleep calls used, and integration tests that measure event loop responsiveness during retries to prevent regression.

## Technical Context

**Language/Version**: Python 3.11–3.13 (workspace `requires-python`)  
**Primary Dependencies**: `openai~=1.60` (LLM provider), `pydantic~=2.10` (config validation), `pytest` (testing)  
**Storage**: N/A — pure library, in-memory retry logic  
**Testing**: `pytest` with `asyncio_mode = "auto"`, 1000s timeout, suites: `unit`, `integration`, `smoke`, `notebook`, `verbs`  
**Target Platform**: Linux server (production), cross-platform compatible library  
**Project Type**: Library — `graphrag-llm` provides LLM client abstractions with retry, rate limiting, caching, and batching middleware  
**Performance Goals**: Async retry backoff must not block event loop — concurrent requests should not experience wall-clock latency proportional to retry delays  
**Constraints**: Must preserve all existing retry configuration semantics (base_delay, max_retries, max_delay, jitter, exceptions_to_skip); metrics output must remain identical  
**Scale/Scope**: `graphrag-llm` is one of 8 workspace packages; affects all LLM callers (completion, embedding) through the retry middleware; downstream consumers include `graphrag` indexing pipeline and `graphrag` query pipeline  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance | Notes |
|---|---|---|
| **I. Library-First Architecture** | ✅ Pass | Change stays within `graphrag-llm`; no new packages needed. Existing `Retry` ABC, `ExponentialRetry`, `ImmediateRetry` are the correct scope. |
| **II. CLI Interface** | ✅ Pass | No CLI surface affected. Retry is internal middleware. |
| **III. Test-First (NON-NEGOTIABLE)** | ✅ Pass | Tests MUST be written before any implementation. This plan's implementation is test coverage additions, all following Red-Green-Refactor. |
| **IV. Integration Testing** | ✅ Pass | Integration test required (SC-004): simulate rate limit retries, verify event loop responsiveness. Existing 5 test suites provide coverage. |
| **V. Versioning & Change Management** | ✅ Pass | semversioner patch change required for any code modification; test additions are patch-level. |

**GATE RESULT**: All gates pass. No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/010-async-retry-system/
├── plan.md              # This file
├── research.md          # Phase 0 output — verification findings
├── data-model.md        # Phase 1 output — N/A (no data entities)
├── quickstart.md        # Phase 1 output — test quickstart
├── contracts/           # Phase 1 output — retry middleware contract
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
packages/graphrag-llm/graphrag_llm/retry/
├── exponential_retry.py     # Target: verify retry_async uses asyncio.sleep
├── immediate_retry.py       # Target: no sleep (no backoff) — verify
├── retry.py                 # ABC: no changes
├── retry_factory.py         # No changes
└── __init__.py              # No changes

packages/graphrag-llm/graphrag_llm/middleware/
├── with_retries.py          # Target: verify routing logic
└── with_errors_for_testing.py  # Target: verify correct sync/async sleep pattern

packages/graphrag-llm/tests/
└── unit/
    └── test_exponential_retry.py    # NEW: unit tests asserting sleep calls
    └── test_with_retries.py         # NEW: unit tests for routing
└── integration/
    └── test_retry_event_loop.py     # NEW: integration test for event loop non-blocking
```

**Structure Decision**: Tests live under `packages/graphrag-llm/tests/` following the existing package-level test convention. No new source files needed — existing code is correct.

## Complexity Tracking

Not applicable — no constitution violations. Minimal change (test additions only).

## Phase 0: Research Findings

### Verification Result: Code is Already Correct

**Decision**: No code changes needed; focus on test coverage.

**Rationale**: Full codebase audit of the retry middleware layer:

| File | Line | Sync Path | Async Path | Status |
|---|---|---|---|---|
| `exponential_retry.py` | 84 | `time.sleep(sleep_delay)` | `await asyncio.sleep(sleep_delay)` (line 115) | ✅ Correct |
| `immediate_retry.py` | 44-61 | No sleep (no backoff) | No sleep (no backoff) | ✅ Correct |
| `with_retries.py` | 47-50 | `retrier.retry(func=sync_middleware)` | `retrier.retry_async(func=async_middleware)` (line 55) | ✅ Correct routing |
| `with_errors_for_testing.py` | 61 | `time.sleep(0.5)` | `await asyncio.sleep(0.5)` (line 74) | ✅ Correct pattern |
| `sliding_window_rate_limiter.py` | 135 | `time.sleep(stagger)` | N/A — sync threading.Lock context | ✅ Acceptable |

**Why the original task was filed**: The upstream V3/main branch (commit `4c8ef97`) had `time.sleep()` in `retry_async()` at line 84. This was fixed to `await asyncio.sleep()` at line 115 in a subsequent change. Our local code is already on the fixed version.

**Alternatives considered**:
1. **Code fix** — rejected: code is already correct
2. **Add assertion-based tests** — selected: verify `asyncio.sleep` is called in async path via mocking
3. **Add event-loop-responsiveness integration tests** — selected: measure actual concurrent request latency

## Phase 1: Design & Contracts

### data-model.md

Not applicable — this feature involves no new data entities, schemas, or persistence. The retry layer operates on in-memory function call wrapping.

### API Contracts

#### Retry Middleware Contract (`with_retries.py`)

The `with_retries()` function returns a tuple of two functions:
- **Sync**: `(func: LLMFunction, input_args: dict) → Any` — wraps sync LLM calls with retry. Uses `retrier.retry()`.
- **Async**: `(func: AsyncLLMFunction, input_args: dict) → Awaitable[Any]` — wraps async LLM calls with retry. Uses `retrier.retry_async()`.

**Invariants**:
- Sync path must use `time.sleep()` for backoff (blocking, correct for sync context)
- Async path must use `await asyncio.sleep()` for backoff (non-blocking, correct for async context)
- Metrics dict is updated in both paths: `retries` (count), `requests_with_retries` (1 if retries > 0)

#### ExponentialRetry Contract (ABC `Retry`)

| Method | Signature | Behavior |
|---|---|---|
| `retry()` | `(func: Callable, input_args: dict) → Any` | Blocking loop with `time.sleep()` backoff |
| `retry_async()` | `(func: AwaitableCallable, input_args: dict) → Awaitable[Any]` | Async loop with `await asyncio.sleep()` backoff |

**Backoff calculation** (identical in both paths):
```
delay *= base_delay
sleep_delay = min(max_delay, delay + (jitter * random.uniform(0, 1)))
```

### quickstart.md

```markdown
# Quickstart: Retry System Tests

## Run retry unit tests
```bash
uv run pytest packages/graphrag-llm/tests/unit/test_exponential_retry.py -v
```

## Run retry routing tests
```bash
uv run pytest packages/graphrag-llm/tests/unit/test_with_retries.py -v
```

## Run event loop responsiveness integration test
```bash
uv run pytest packages/graphrag-llm/tests/integration/test_retry_event_loop.py -v --run_slow
```

## Run all graphrag-llm tests
```bash
uv run pytest packages/graphrag-llm/tests/ -v
```

## Full check
```bash
uv run poe check
```
```

### Agent Context Update

<tool_call>
<function=bash>
<parameter=command>
test -f .specify/scripts/bash/update-agent-context.sh && .specify/scripts/bash/update-agent-context.sh opencode 2>&1 || echo "Script not found or failed"