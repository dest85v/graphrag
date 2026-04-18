---

description: "Task list for fixing CI pre-existing errors"

---

# Tasks: Fix CI Pre-existing Errors

**Input**: Design documents from `/specs/008-fix-ci-errors/`
**Prerequisites**: plan.md (required), spec.md (required), research.md (required), data-model.md, quickstart.md

**Tests**: Not requested — this is a CI maintenance fix, not a feature implementation.

**Organization**: Tasks are organized by the CI errors being fixed, aligned with the two user stories from spec.md.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify current error state and prepare for fixes

- [X] T001 Run `uv run poe check` and capture baseline error count (9 errors: 3 ruff + 6 pyright)
- [X] T002 [P] Verify `tokenizers` is not installed in `.venv` by running `uv pip list | grep tokenizers`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fix the root cause affecting the most errors

**⚠️ CRITICAL**: This fix resolves 6 of 9 errors and must be completed first

- [X] T003 [US1] Move `tokenizers>=0.21,<0.23` from `[project.optional-dependencies]` (huggingface extra) to base `dependencies` in `packages/graphrag-llm/pyproject.toml` line 48
- [X] T004 [US1] Run `uv sync` to install `tokenizers` into `.venv`
- [X] T005 [US1] Verify pyright resolves `tokenizers` imports: run `uv run pyright` — expect 0 `reportMissingImports` errors (down from 6)

**Checkpoint**: `tokenizers` fix validated — 6/9 CI errors resolved

---

## Phase 3: User Story 1 — Fix ruff errors (Priority: P1) 🎯 MVP

**Goal**: Resolve all 3 remaining ruff errors so `ruff check .` passes cleanly

**Independent Test**: Run `uv run poe check` — expect exit code 0 with zero errors

### Implementation

- [X] T006 [US1] Add `SLF001` to `[tool.ruff.lint.per-file-ignores]` for `tests/*` pattern in root `pyproject.toml` line 227
- [X] T007 [US1] Add `RUF001` to `[tool.ruff.lint.per-file-ignores]` for `tests/*` pattern in root `pyproject.toml` line 227
- [X] T008 [US1] Run `uv run poe check` — expect 0 errors, 0 warnings. Confirm all 9 original errors are resolved

**Checkpoint**: `poe check` passes with exit code 0 — all CI errors fixed

---

## Phase 4: Polish & Validation

**Purpose**: Verify zero regressions and document the fix

- [X] T009 [P] Run `uv run poe test` to verify all existing tests pass (zero regressions)
- [X] T010 [P] Run `uv run poe test_unit` to verify unit test suite specifically passes
- [X] T011 [P] Run `uv run poe test_integration` to verify integration test suite specifically passes
- [X] T012 Update `docs/research/packages_todos.md` — mark P0 pre-existing CI errors task as complete with fix summary
- [X] T013 Run `uv run semversioner add-change -t patch -d "Fix 9 CI errors: tokenizers import resolution, SLF001 and RUF001 false-positives in test files."`
- [X] T014 Run final `uv run poe check` validation — confirm 0 errors, 0 warnings
- [X] T015 Run `uv run poe format` to verify auto-formatting applies no changes (clean format)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS ruff fixes (tokenizers must be installed before pyright validates)
- **User Story 1 (Phase 3)**: Depends on Foundational completion — ruff fixes independent of tokenizers but both contribute to `poe check`
- **Polish (Phase 4)**: Depends on all fixes being complete

### Parallel Opportunities

- T001 and T002 (Phase 1) can run in parallel
- T009, T010, T011 (Phase 4) can run in parallel (different test suites)
- T006 and T007 (Phase 3) can run in parallel (same file, different lines — but both edit `pyproject.toml` so should be combined into a single edit)

### Within Each Phase

- Verify each fix before proceeding to next phase
- Run `poe check` incrementally to confirm error count decreases

---

## Parallel Example: Phase 4 Validation

```bash
# Run all test suites in parallel:
Task: "Run `uv run poe test_unit` to verify unit tests pass"
Task: "Run `uv run poe test_integration` to verify integration tests pass"
Task: "Run `uv run poe test_smoke` to verify smoke tests pass"
```

---

## Implementation Strategy

### MVP (Phases 1-3)

1. Complete Phase 1: Setup — capture baseline
2. Complete Phase 2: Fix `tokenizers` dependency (6/9 errors)
3. Complete Phase 3: Fix ruff ignores (3/9 errors)
4. **STOP and VALIDATE**: Run `poe check` — expect exit code 0

### Full Delivery (All Phases)

1. Complete MVP validation
2. Add Phase 4: Run all test suites, update docs, add semversioner entry
3. Final validation: `poe check` + `poe test` both green

---

## Notes

- Total tasks: 15
- Tasks per user story: US1 = 7 (T003-T008), US2 not applicable (single story, both ruff fixes)
- All tasks target file modifications in 2 files: `packages/graphrag-llm/pyproject.toml` and root `pyproject.toml`
- T006 and T007 edit the same file — should be combined into a single edit operation
- No new tests required — this is a CI maintenance fix
