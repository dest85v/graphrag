# Implementation Plan: Fix Middleware Exception Logging

**Branch**: `001-middleware-exception-logging` | **Date**: 2026-04-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-middleware-exception-logging/spec.md`

## Summary

Eliminate silent exception swallowing in three files: `with_cache.py` (graphrag-llm), `mcp/middleware.py` (graphrag-llm), and `search.py` (graphrag). Most exception handlers already log with `logger.exception()` / `log.exception()`. The remaining gaps are: (1) MCP async path catches `Exception` but does not add to the `exceptions` list like the sync path does, (2) MCP sync path catches `Exception` without logging, and (3) some `# noqa: BLE001` broad-except blocks lack logging calls entirely. All changes are additive — no control-flow behavior changes, no API surface changes.

## Technical Context

**Language/Version**: Python 3.11–3.13 (workspace constraint)  
**Primary Dependencies**: Python standard library `logging` module  
**Storage**: N/A  
**Testing**: pytest with `asyncio_mode = "auto"`, 1000s default timeout  
**Target Platform**: Linux server (GraphRAG pipeline / query engine)  
**Project Type**: Library (Python package monorepo, 8 packages)  
**Performance Goals**: N/A — logging is additive, no performance-sensitive path  
**Constraints**: No control-flow changes; exception handling behavior must remain: catch → log → continue/graceful degradation  
**Scale/Scope**: 3 files, ~15 exception handlers total, all within `graphrag-llm` (2 files) and `graphrag` (1 file)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Library-First Architecture
**PASS** — Changes are confined to existing packages (`graphrag-llm`, `graphrag`). No new libraries created.

### II. CLI Interface
**PASS** — No CLI changes. Internal logging improvement.

### III. Test-First (NON-NEGOTIABLE)
**PASS** — Tests will be written to verify logging behavior before implementation changes. Existing tests must pass (SC-004).

### IV. Integration Testing
**PASS** — Changes affect cross-package behavior (cache middleware is used by both completion and embedding paths). Integration tests validate cache + LLM pipeline.

### V. Versioning & Change Management
**PASS** — semversioner PATCH change entry required before merge (minor internal visibility fix).

**GATE RESULT**: All gates pass. No violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/001-middleware-exception-logging/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (not applicable — no new entities)
├── quickstart.md        # Phase 1 output (not applicable — no new features for users)
├── contracts/           # Phase 1 output (not applicable — no interface changes)
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
packages/graphrag-llm/graphrag_llm/middleware/with_cache.py          # Change: add logging
packages/graphrag-llm/graphrag_llm/mcp/middleware.py                 # Change: add logging + fix sync/async consistency
packages/graphrag/graphrag/query/structured_search/global_search/search.py  # Verify logging already adequate
tests/unit/middleware/test_with_cache_logging.py                     # New: cache exception logging tests
tests/unit/mcp/test_middleware_logging.py                            # New: MCP exception logging tests
```

**Structure Decision**: No new modules or directories needed. Changes are additive logging statements and one consistency fix in existing files.

## Complexity Tracking

Not applicable — no constitution violations.
