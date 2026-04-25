# Implementation Plan: Async Non-Blocking Retry Sleep

**Branch**: `010-async-retry-system` | **Date**: 2026-04-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/010-async-retry-system/spec.md`

## Summary

The P0 task flagged `time.sleep()` in the `graphrag-llm` retry layer as blocking the event loop. Full codebase audit confirms the async path in `ExponentialRetry.retry_async()` already uses `await asyncio.sleep()` — the code was fixed in upstream V3/main. This plan shifts from "code fix" to **test coverage**: adding unit tests that assert the correct sleep function is called in each path, plus integration tests measuring event loop responsiveness during retries.

## Technical Context

**Language/Version**: Python 3.11–3.13 (workspace `requires-python`)  
**Primary Dependencies**: `openai~=1.60` (LLM provider), `pydantic~=2.10` (config validation), `pytest` + `pytest-asyncio` (testing)  
**Storage**: N/A — pure library, in-memory retry logic  
**Testing**: `pytest` with `asyncio_mode = "auto"`, 1000s timeout. Suites: `unit`, `integration`, `smoke`, `notebook`, `verbs`  
**Target Platform**: Linux server (production), cross-platform compatible library  
**Project Type**: Library — `graphrag-llm` provides LLM client abstractions with retry, rate limiting, caching, and batching middleware  
**Performance Goals**: Async retry backoff must not block event loop — concurrent requests should not experience wall-clock latency proportional to retry delays  
**Constraints**: Must preserve all existing retry configuration semantics (base_delay, max_retries, max_delay, jitter, exceptions_to_skip); metrics output must remain identical  
**Scale/Scope**: `graphrag-llm` is one of 8 workspace packages; affects all LLM callers (completion, embedding) through the retry middleware  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance | Post-Design Re-evaluation |
|---|---|---|
| **I. Library-First Architecture** | ✅ Pass | ✅ Pass — Test additions stay within `graphrag-llm`, no new packages |
| **II. CLI Interface** | ✅ Pass | ✅ Pass — No CLI surface affected |
| **III. Test-First (NON-NEGOTIABLE)** | ✅ Pass | ✅ Pass — Tests are written before implementation (tests are the deliverable) |
| **IV. Integration Testing** | ✅ Pass | ✅ Pass — Integration test added: event loop responsiveness |
| **V. Versioning & Change Management** | ✅ Pass | ✅ Pass — Test additions are patch-level semversioner change |

**GATE RESULT**: All gates pass. No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/010-async-retry-system/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output — verification findings
├── data-model.md        # Phase 1 output — N/A (no data entities)
├── quickstart.md        # Phase 1 output — test quickstart
├── contracts/
│   └── retry-middleware.md  # Phase 1 output — retry interface contracts
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

tests/
├── unit/
│   └── retry/
│       ├── __init__.py
│       ├── test_exponential_retry.py    # NEW: unit tests asserting sleep calls
│       └── test_with_retries.py         # NEW: unit tests for routing
└── integration/
    └── retry/
        ├── __init__.py
        └── test_retry_event_loop.py     # NEW: integration test for event loop non-blocking
```

**Structure Decision**: Tests live under top-level `tests/unit/` and `tests/integration/` following the existing monorepo test convention. No new source files needed — existing code is already correct.

## Complexity Tracking

Not applicable — no constitution violations. Minimal change (test additions only).
