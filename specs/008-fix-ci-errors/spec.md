# Feature Specification: Fix CI Pre-existing Errors

**Feature Branch**: `008-fix-ci-errors`  
**Created**: 2026-04-18  
**Status**: Draft  
**Input**: User description: "P0 — CI pre-existing errors: pyproject.toml, tokenizers, RUF001 кириллица, graphrag-cache, pyright type errors"

## User Scenarios & Testing

### User Story 1 — Developer can run `poe check` without errors (Priority: P1)

Every developer and CI pipeline runs `poe check` (ruff format + ruff check + pyright) before committing. Currently it fails with 9 errors (3 ruff + 6 pyright), blocking all PR merges and obscuring real regressions.

**Why this priority**: P0 blocker — no PR can pass CI until these errors are resolved. Every contributor needs a clean `poe check` to validate their changes.

**Independent Test**: Run `uv run poe check` — expect 0 errors, 0 warnings.

**Acceptance Scenarios**:

1. **Given** the repo is checked out with `uv sync` dependencies installed, **When** `uv run poe check` is executed, **Then** the exit code is 0 with zero ruff and zero pyright errors
2. **Given** the CI pipeline runs `poe check`, **When** a PR is opened, **Then** the CI check passes (green)

### User Story 2 — Pyright resolves all `tokenizers` imports (Priority: P1)

The HuggingFace tokenizer implementation (`P3 — HuggingFace tokenizers`) depends on the `tokenizers` library. Pyright cannot resolve `import tokenizers` in 6 files because the package is not installed in the dev environment.

**Why this priority**: Blocks HuggingFace tokenizer feature (P3) from having passing type checks. Developers get noisy errors when editing any file that imports `tokenizers`.

**Independent Test**: Run `uv run pyright` on files importing `tokenizers` — expect 0 `reportMissingImports` errors.

**Acceptance Scenarios**:

1. **Given** `graphrag-llm/pyproject.toml` lists `tokenizers` as a dependency, **When** `uv sync` runs, **Then** `tokenizers` is installed in `.venv`
2. **Given** `tokenizers` is installed, **When** pyright analyzes files with `from tokenizers import ...`, **Then** no `reportMissingImports` errors appear

---

### Edge Cases

- `tokenizers` is a Rust-based library with native extensions — installation may fail on unusual platforms. The fix must work on standard Linux/macOS CI runners.
- If `tokenizers` was previously listed under `[project.optional-dependencies]`, moving it to base dependencies increases install size for all users.
- Existing CI errors mentioned in the original P0 task (graphrag-cache missing, pyright type expressions in graphrag-llm, build-system empty) may have been partially fixed. This spec covers only the errors currently observed.

## Requirements

### Functional Requirements

- **FR-001**: `uv run poe check` MUST pass with zero errors and zero warnings after fixes
- **FR-002**: The `tokenizers` Python package MUST be resolvable by pyright in all files that import it (6 locations)
- **FR-003**: The `tokenizers` dependency MUST be installed in the dev environment by `uv sync` (not just in optional extras)
- **FR-004**: Fixes MUST NOT change runtime behavior, API surfaces, or existing test semantics
- **FR-005**: RUF001 Cyrillic false-positives in test files MUST be suppressed (via `noqa` or ruff config), not removed

### Key Entities

- **`tokenizers`**: HuggingFace Rust-based tokenizer library, required by `HuggingFaceTokenizer` in `graphrag-llm`. Currently listed in `graphrag-llm/pyproject.toml` but not resolved by pyright.
- **RUF001**: Ruff rule detecting ambiguous Unicode characters (Cyrillic visually identical to Latin). Fires on test assertions containing Cyrillic stop words.
- **poe check**: Composite task running `ruff format --check`, `ruff check`, and `pyright` sequentially.

## Success Criteria

### Measurable Outcomes

- **SC-001**: `poe check` completes with exit code 0 (zero ruff errors, zero pyright errors)
- **SC-002**: All 6 pyright `reportMissingImports` errors for `tokenizers` are resolved
- **SC-003**: All 2 RUF001 errors for Cyrillic strings are suppressed
- **SC-004**: All existing unit, integration, and chunking tests continue to pass after fixes (zero regressions)

## Assumptions

- The `tokenizers` package is already listed in `graphrag-llm/pyproject.toml` but installed as optional/extras — the fix is to move it to base dependencies or ensure `uv sync` picks up the optional extra.
- The SLF001 error on `_nltk_language` (from feature 007) is also present in CI and should be fixed as part of this task (access private member in test).
- The graphrag-cache and graphrag-llm pyright type expression errors mentioned in the original P0 task documentation have already been resolved; only the currently observed 9 errors are actionable.
- The `[build-system]` issue in `packages/graphrag/pyproject.toml` was partially fixed during feature 007 implementation; no further action needed unless `uv build --all-packages` is broken.
