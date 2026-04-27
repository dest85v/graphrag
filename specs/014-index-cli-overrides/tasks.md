---

description: "Task list for CLI Index/Update Overrides feature"
---

# Tasks: CLI Index/Update Overrides

**Input**: Design documents from `/specs/014-index-cli-overrides/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli-set-flag.md, quickstart.md

**Tests**: Test-first approach per Constitution Principle III. Tests written before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare test infrastructure for the feature

- [x] T001 Create test directory `packages/graphrag/tests/unit/cli/` with `__init__.py`
- [x] T002 Create test directory `packages/graphrag/tests/integration/` with `__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement the `--set` flag parsing utility that all user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 [P] Write unit tests for `parse_set_args` in `tests/unit/cli/test_cli_overrides.py` covering: dot-notation nesting, multiple flags, `=` in values, empty key error, missing `=` error, last-wins conflict
- [x] T004 Create `packages/graphrag/graphrag/cli/overrides.py` with `parse_set_args(set_args: list[str]) -> dict[str, Any]` function implementing dot-notation to nested dict conversion, `=` partition splitting, empty key rejection
- [x] T005 Run T003 tests — confirm they FAIL before T004 implementation

**Checkpoint**: Foundation ready — `parse_set_args` utility is implemented and tested. Both `index` and `update` commands will use this same function.

---

## Phase 3: User Story 1 — Override config at index time (Priority: P1) 🎯 MVP

**Goal**: Users can run `graphrag index --set key=value` to override config fields without editing `settings.yaml`

**Independent Test**: `graphrag index --set completion_models.default.model=gpt-4o --dry-run` on a project with `settings.yaml` — the dry-run log shows `gpt-4o` as the model.

### Implementation for User Story 1

- [x] T006 [P] [US1] Add `--set` optional argument to `_index_cli` in `packages/graphrag/graphrag/cli/main.py`: `set_args: list[str] = typer.Option([], "--set", "-s", help="Override config values (key=value, repeatable)")`
- [x] T007 [P] [US1] Import `parse_set_args` from `graphrag.cli.overrides` in `packages/graphrag/graphrag/cli/main.py`
- [x] T008 [US1] Convert `set_args` to overrides dict and pass to `index_cli()` call in `_index_cli` in `packages/graphrag/graphrag/cli/main.py`
- [x] T009 [US1] Add `cli_overrides: dict[str, Any] | None = None` parameter to `index_cli()` in `packages/graphrag/graphrag/cli/index.py`
- [x] T010 [US1] Forward `cli_overrides` to `load_config()` call in `index_cli()` in `packages/graphrag/graphrag/cli/index.py`
- [x] T011 Run T003 tests again — confirm all pass (no regression in `parse_set_args`)
- [x] T012 [US1] Smoke-test: `graphrag index --set cache.type=Noop --dry-run` and verify no errors

**Checkpoint**: User Story 1 is fully functional — `--set` works end-to-end for `graphrag index`.

---

## Phase 4: User Story 2 — Override config at update time (Priority: P1)

**Goal**: Users can run `graphrag update --set key=value` to override config fields for incremental updates

**Independent Test**: `graphrag update --set output_storage.base_dir=./custom_update --dry-run` on an indexed project — the dry-run log shows the overridden output directory.

### Implementation for User Story 2

- [x] T013 [P] [US2] Add `--set` optional argument to `_update_cli` in `packages/graphrag/graphrag/cli/main.py`: same signature as in `_index_cli`
- [x] T014 [US2] Convert `set_args` to overrides dict and pass to `update_cli()` call in `_update_cli` in `packages/graphrag/graphrag/cli/main.py`
- [x] T015 [US2] Add `cli_overrides: dict[str, Any] | None = None` parameter to `update_cli()` in `packages/graphrag/graphrag/cli/index.py`
- [x] T016 [US2] Forward `cli_overrides` to `load_config()` call in `update_cli()` in `packages/graphrag/graphrag/cli/index.py`
- [x] T017 [US2] Smoke-test: `graphrag update --set cache.type=Noop --dry-run` and verify no errors (note: `update` does not support `--dry-run` currently, verify behavior)
- [x] T018 [US2] Verify no regression: `graphrag update` without `--set` flags works exactly as before

**Checkpoint**: User Stories 1 AND 2 both work — `--set` works for both `index` and `update` commands.

---

## Phase 5: User Story 3 — Discover available overrides via help (Priority: P2)

**Goal**: `graphrag index --help` and `graphrag update --help` display the `--set` flag with clear documentation

**Independent Test**: Run `graphrag index --help` and `graphrag update --help` — both show `--set`/`-s` with description text.

### Implementation for User Story 3

- [x] T019 [US3] Verify help text in `--set` option description is clear and includes examples (review T006, T013 help strings)
- [x] T020 [US3] Run `graphrag index --help` and `graphrag update --help` to confirm `--set` flag appears with description

**Checkpoint**: All user stories complete — `--set` is discoverable via `--help`.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup, regression verification, and documentation

- [x] T021 [P] Run `uv run poe check` on modified files — verify 0 lint errors, 0 type errors
- [x] T022 [P] Run `uv run poe test_unit` — verify all existing unit tests pass (no regression)
- [x] T023 Run integration tests for `index` and `update` commands — verify no regression
- [x] T024 [P] Add semversioner PATCH change entry: `uv run semversioner add-change -t patch -d "Add --set CLI override flag to index and update commands."`
- [x] T025 [P] Verify quickstart.md examples work end-to-end (run each example command from quickstart.md)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US1)**: Depends on Phase 2 completion
- **Phase 4 (US2)**: Depends on Phase 2 completion (can parallelize with Phase 3)
- **Phase 5 (US3)**: Depends on Phases 3 and 4 (help text needs flags to exist)
- **Phase 6 (Polish)**: Depends on all desired user stories being complete

### Parallel Opportunities

- T001 and T002 (Phase 1) — parallel directory creation
- T003 and T004 (Phase 2) — tests and implementation can be written in parallel (but T003 must pass before T004)
- T006-T008 and T013-T016 (Phases 3/4) — index and update changes are parallelizable (different functions in different files)
- T021-T025 (Phase 6) — can run in parallel where tools allow

### Within Each User Story

- Tests MUST be written and FAIL before implementation (Red-Green-Refactor)
- Models/utilities before handlers
- Handlers before integration verification

---

## Parallel Example: Phase 3 + Phase 4

```bash
# Launch index changes (Phase 3):
Task: "Add --set optional argument to _index_cli in main.py"
Task: "Add cli_overrides param to index_cli() in index.py"
Task: "Forward cli_overrides to load_config() in index.py"

# Launch update changes (Phase 4) in parallel:
Task: "Add --set optional argument to _update_cli in main.py"
Task: "Add cli_overrides param to update_cli() in index.py"
Task: "Forward cli_overrides to load_config() in index.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (`parse_set_args` utility + tests)
3. Complete Phase 3: User Story 1 (`index` command)
4. **STOP and VALIDATE**: `graphrag index --set cache.type=Noop --dry-run` works
5. This is a fully functional MVP — users can override config for indexing

### Incremental Delivery

1. Phase 1 + 2 → Foundation ready
2. Phase 3 → `graphrag index --set` works (MVP!)
3. Phase 4 → `graphrag update --set` works
4. Phase 5 → Help text verified
5. Phase 6 → Clean up, regression tests, semversioner

### Parallel Team Strategy

With multiple developers:
1. Team completes Phase 1 + 2 together
2. Once Phase 2 is done:
   - Developer A: Phase 3 (index changes)
   - Developer B: Phase 4 (update changes)
3. Both complete independently — both pass `poe check` and tests

---

## Notes

- Total tasks: 25
- Test-first: T003 (tests for parse_set_args) written before T004 (implementation)
- No new dependencies — uses only existing `typer` and `_recursive_merge_dicts`
- Zero API changes to `load_config()` — backward compatible
- `--set` follows Docker/Helm/Pulumi convention for CLI overrides
