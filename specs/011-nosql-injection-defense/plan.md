# Implementation Plan: Nosql Injection Defense

**Branch**: `012-nosql-injection-defense` | **Date**: 2026-04-26 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/011-nosql-injection-defense/spec.md`

## Summary

Fix a P1 NoSQL injection vulnerability in Azure Cosmos DB query construction across two packages: `graphrag-storage` (`AzureCosmosStorage`) and `graphrag-vectors` (`CosmosDBVectorStore`). The fix introduces a centralized `_sanitize_cosmos_key()` utility for escaping backslashes and double quotes in user-supplied string values interpolated into SQL-like query strings, adds validation of configurable field names against a safe identifier pattern (`[a-zA-Z_][a-zA-Z0-9_]*`), and ensures consistent sanitization at all query construction points with security logging.

## Technical Context

**Language/Version**: Python 3.11–3.13 (workspace `requires-python = ">=3.11,<3.14"`)  
**Primary Dependencies**: `azure-cosmos` SDK (both packages), `pydantic` (config validation)  
**Storage**: Azure Cosmos DB SQL API  
**Testing**: pytest with `asyncio_mode = "auto"`, 1000s default timeout; test suites: `unit`, `integration`, `smoke`  
**Target Platform**: Linux servers running GraphRAG workloads  
**Project Type**: Library (monorepo with 8 packages)  
**Performance Goals**: Negligible overhead — sanitization is O(n) string operation on keys typically < 256 chars  
**Constraints**: Zero breaking changes for existing valid inputs; backward compatible with all existing field names and file names  
**Scale/Scope**: 2 packages affected, ~7 query construction points, ~10 unit tests + edge case coverage  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Constitution Principle | Compliance | Notes |
|---|---|---|
| **I. Library-First Architecture** | ✅ PASS | Fix is scoped to existing packages (`graphrag-storage`, `graphrag-vectors`); new utility lives in each package as an internal module |
| **II. CLI Interface** | ✅ PASS | No CLI changes — this is an internal security fix |
| **III. Test-First (NON-NEGOTIABLE)** | ✅ PASS | Tests will be written before implementation per Red-Green-Refactor cycle |
| **IV. Integration Testing** | ✅ PASS | Mocked CosmosDB client tests for both storage and vector store layers |
| **V. Versioning & Change Management** | ✅ PASS | semversioner PATCH entry will be added (security fix, backward compatible) |
| **Security: No secrets in code** | ✅ PASS | Fix does not introduce any secrets; sanitization is a general utility |

**Result**: ALL GATES PASS — no violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/011-nosql-injection-defense/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
packages/graphrag-storage/graphrag_storage/
├── azure_cosmos_storage.py          # ← Sanitization added at query construction points
├── cosmos_sanitizer.py              # ← NEW: centralized _sanitize_cosmos_key() utility
└── test_cosmos_sanitizer.py         # ← NEW: unit tests for sanitizer

packages/graphrag-vectors/graphrag_vectors/
├── cosmosdb.py                      # ← Field name validation + sanitization added
├── cosmos_sanitizer.py              # ← NEW: shared _sanitize_cosmos_key() utility (same as storage)
└── test_cosmos_sanitizer.py         # ← NEW: unit tests for sanitizer

tests/unit/
├── test_cosmos_storage_security.py  # ← NEW: malicious key injection tests for AzureCosmosStorage
└── test_cosmos_vector_security.py   # ← NEW: malicious field name injection tests for CosmosDBVectorStore
```

**Structure Decision**: Each affected package gets its own `cosmos_sanitizer.py` module. The sanitizer utility is self-contained and may be extracted to `graphrag-common` in a future refactoring if more packages need it. Sanitization is applied at the query construction point (inline call to `_sanitize_cosmos_key()`), not at input time, to preserve original values for logging/debugging while ensuring queries are always safe.

## Complexity Tracking

Not applicable — Constitution Check has no violations.

## Phase 0: Research & Decisions

### Research Findings

**Decision 1: Sanitization strategy — escape vs. reject**
- **Chosen**: Escape special characters (backslashes, double quotes) in string values interpolated into query strings. This preserves legitimate file names containing apostrophes, quotes, or backslashes.
- **Rationale**: FR-001 requires escaping, not rejection. Cosmos DB SQL API uses double-quoted strings in query literals, so escaping `"` as `\"` and `\` as `\\` is the standard approach.
- **Alternatives considered**: (a) Reject all non-alphanumeric keys — too aggressive, breaks legitimate file names with spaces/special chars; (b) Use parameterized queries for all values — Cosmos DB SQL API supports `@param` syntax for some operations but NOT for string literals in `STARTSWITH()`, `CONTAINS()`, etc., so escaping is the only viable approach for these query patterns.

**Decision 2: Field name validation — reject at config time**
- **Chosen**: Validate field names against `[a-zA-Z_][a-zA-Z0-9_]*` pattern during `__init__`/`connect()` time. Reject invalid field names immediately with a clear error message.
- **Rationale**: Field names (`id_field`, `vector_field`, `create_date_field`) are configuration-time values, not runtime user input. Validating them at construction time prevents any query execution with unsanitized identifiers. FR-002 requires this pattern.
- **Alternatives considered**: (a) Sanitize field names at query time — dangerous, a sanitized field name could differ from the intended schema; (b) Allow any string and escape — Cosmos DB identifiers cannot contain special characters, so escaping is not a valid approach for field names.

**Decision 3: Shared utility vs. per-package utility**
- **Chosen**: Duplicate the `_sanitize_cosmos_key()` function in both packages (`graphrag-storage` and `graphrag-vectors`). Keep it as a private module (`cosmos_sanitizer.py`) within each package.
- **Rationale**: The function is trivially small (2-character replacement). Extracting to `graphrag-common` would add dependency complexity for a 3-line function. Both packages already have independent Azure Cosmos DB dependencies.
- **Alternatives considered**: (a) Single shared module in `graphrag-common` — adds package dependency, potential circular import risk; (b) Inline the escape logic at each call site — DRY violation, error-prone.

**Decision 4: Logging sanitization events**
- **Chosen**: `logger.warning("Cosmos DB query sanitization applied: escaped %d characters in field '%s'", count, field_name)` when any escape is applied. The original value is NOT logged (security best practice).
- **Rationale**: FR-006 requires logging when sanitization is applied. Logging the sanitized value (not the original) avoids exposing potentially sensitive file names in logs.
- **Alternatives considered**: (a) Log at `INFO` level — too noisy for production; (b) Log at `ERROR` level — sanitization is expected behavior, not an error; (c) Don't log — operator has no visibility into sanitization events.

**Decision 5: Cosmos DB emulator testing**
- **Chosen**: Use mocked `ContainerProxy` and `CosmosClient` objects. No real Cosmos DB instance or emulator needed.
- **Rationale**: Per spec assumptions, tests use mocked clients. The sanitizer is pure string manipulation — no network calls, no emulator-specific behavior to test.
- **Alternatives considered**: (a) Integration test with Cosmos DB emulator — adds Docker dependency, slows CI; (b) Integration test with real Cosmos DB — requires credentials, not suitable for CI.

## Phase 1: Design & Contracts

### Data Model

This feature does not introduce new data entities or schema changes. It modifies how existing data (storage keys, field names) is handled in query construction.

**Entities (existing, no changes)**:
- **Storage Key** (string): File name / document identifier — now sanitized before query interpolation
- **Field Name** (string): Now validated against `[a-zA-Z_][a-zA-Z0-9_]*` pattern at config time
- **Query Filter** (string): Filter expression — already compiled via `_compile_filter()`, no changes needed for filter values (they use parameter syntax in some operators, string literals in others — all escaped via sanitizer)

### Quickstart

To verify the NoSQL injection defense:

1. **Run sanitizer unit tests** (must pass):
   ```bash
   uv run poe test_only "test_cosmos_sanitizer"
   ```

2. **Run security injection tests** (must pass):
   ```bash
   uv run poe test_only "test_cosmos_storage_security"
   uv run poe test_only "test_cosmos_vector_security"
   ```

3. **Run full test suite** (zero regressions):
   ```bash
   uv run poe test_unit
   ```

4. **Run full check** (format + lint + typecheck):
   ```bash
   uv run poe check
   ```

5. **Verify injection payloads are neutralized** (manual inspection):
   - Storage layer: `AzureCosmosStorage._get_prefix("entities'; DROP DATABASE --")` → sanitized prefix used in `STARTSWITH()`
   - Vector store: `CosmosDBVectorStore` with `id_field="id\" OR 1=1 --"` → rejected at initialization

### Implementation Tasks (detailed)

See `tasks.md` (generated by `/speckit.tasks`) for the full task breakdown.

| # | File | Change |
|---|---|---|
| 1 | `packages/graphrag-storage/graphrag_storage/cosmos_sanitizer.py` | NEW: `_sanitize_cosmos_key(key: str) -> str` — escapes `\` → `\\` and `"` → `\"`; logs warning when escaping occurs |
| 2 | `packages/graphrag-storage/azure_cosmos_storage.py` | Import sanitizer; apply `_sanitize_cosmos_key()` at lines 198, 376 (STARTSWITH prefix); sanitize `query_filter` at line 358 |
| 3 | `packages/graphrag-vectors/graphrag_vectors/cosmos_sanitizer.py` | NEW: Same sanitizer utility (copy from storage package) |
| 4 | `packages/graphrag-vectors/graphrag_vectors/cosmosdb.py` | Add Pydantic validator for `id_field`/`vector_field` against `[a-zA-Z_][a-zA-Z0-9_]*` pattern; apply sanitizer in `similarity_search_by_vector` for `id_field`, `vector_field`, and field names in `field_selections` |
| 5 | `tests/unit/test_cosmos_sanitizer.py` (both packages) | NEW: Test `_sanitize_cosmos_key()` with normal, special-char, and injection payloads |
| 6 | `tests/unit/test_cosmos_storage_security.py` | NEW: Mocked tests for `AzureCosmosStorage` with malicious keys |
| 7 | `tests/unit/test_cosmos_vector_security.py` | NEW: Mocked tests for `CosmosDBVectorStore` with malicious field names |
| 8 | `pyproject.toml` | Update ruff per-file-ignores if new test paths are outside existing patterns |

### Constitution Check (Post-Design Re-evaluation)

| Constitution Principle | Compliance | Notes |
|---|---|---|
| **I. Library-First Architecture** | ✅ PASS | Scoped to existing packages, no new packages |
| **II. CLI Interface** | ✅ PASS | No CLI changes |
| **III. Test-First** | ✅ PASS | Test files listed above will be created before implementation |
| **IV. Integration Testing** | ✅ PASS | Mocked tests cover both packages |
| **V. Versioning** | ✅ PASS | semversioner PATCH entry planned |
| **Security** | ✅ PASS | Fix ADDS security, does not weaken it |

**Result**: ALL GATES STILL PASS post-design.

## Artifacts Generated

- **Branch**: `012-nosql-injection-defense`
- **IMPL_PLAN**: `specs/011-nosql-injection-defense/plan.md`
- **research.md**: `specs/011-nosql-injection-defense/research.md` (generated below)
- **data-model.md**: `specs/011-nosql-injection-defense/data-model.md` (generated below)
- **quickstart.md**: `specs/011-nosql-injection-defense/quickstart.md` (generated below)
