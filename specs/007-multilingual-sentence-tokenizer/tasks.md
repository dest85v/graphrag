---

description: "Task list for NLTK Multilingual Sentence Tokenizer feature"
---

# Tasks: NLTK Multilingual Sentence Tokenizer

**Input**: Design documents from `/specs/007-multilingual-sentence-tokenizer/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Written before implementation per Constitution Principle III (Test-First, NON-NEGOTIABLE).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Chunking package**: `packages/graphrag-chunking/graphrag_chunking/`
- **Config package**: `packages/graphrag/graphrag/config/`
- **Tests**: `packages/graphrag-chunking/tests/` (unit) and `tests/` (integration)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Ensure repo state is clean and test infrastructure is ready

- [X] T001 Verify `uv sync` completes without errors in workspace
- [X] T002 Verify `poe check` passes on `research` branch (baseline)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add `nltk_language` field to data model and defaults — the foundational config change that all user stories depend on

**⚠️ CRITICAL**: No user story implementation can begin until this phase is complete.

- [X] T003 Add `nltk_language: str = "english"` field to `ChunkingConfig` in `packages/graphrag-chunking/graphrag_chunking/chunking_config.py`
- [X] T004 Add `nltk_language: str = "english"` to `ChunkingDefaults` dataclass in `packages/graphrag/graphrag/config/defaults.py`

**Checkpoint**: Foundation ready — config field exists, defaults set, backward compatible (default `"english"`).

---

## Phase 3: User Story 1 — Russian Sentence Chunking (Priority: P1) 🎯 MVP

**Goal**: Users can set `chunking.type: sentence` + `nltk_language: russian` in config and get correct Russian sentence splitting via NLTK Punkt.

**Independent Test**: Run `SentenceChunker(nltk_language="russian")` on Russian text and verify correct sentence boundaries.

### Tests for User Story 1

> **NOTE**: Write these tests FIRST, ensure they FAIL before implementation.

- [X] T005 [P] [US1] Create unit test file `tests/unit/indexing/chunking/test_sentence_chunker_nltk_language.py`
- [X] T006 [US1] Implement test: `test_sentence_chunker_russian_language` — verify Russian text splits into correct sentences with `nltk_language="russian"` in `tests/unit/indexing/chunking/test_sentence_chunker_nltk_language.py`
- [X] T007 [US1] Implement test: `test_sentence_chunker_english_default` — verify `nltk_language="english"` works for English text in `tests/unit/indexing/chunking/test_sentence_chunker_nltk_language.py`

### Implementation for User Story 1

- [X] T008 [US1] Modify `SentenceChunker.__init__()` in `packages/graphrag-chunking/graphrag_chunking/sentence_chunker.py` to accept `nltk_language: str = "english"` parameter
- [X] T009 [US1] Modify `SentenceChunker.chunk()` in `packages/graphrag-chunking/graphrag_chunking/sentence_chunker.py` to pass `language=self._nltk_language` to `nltk.sent_tokenize()`
- [X] T010 [US1] Add `bootstrap_nltk.py` test: verify `punkt_tab` is downloaded by `bootstrap()` in `packages/graphrag-chunking/tests/unit/test_bootstrap_nltk.py`

### Integration for User Story 1

- [X] T011 [US1] Verify `create_chunker()` in `packages/graphrag-chunking/graphrag_chunking/chunker_factory.py` passes `nltk_language` via `**kwargs` (no code change needed, verify existing behavior)

**Checkpoint**: At this point, User Story 1 is fully functional — Russian sentence chunking works end-to-end.

---

## Phase 4: User Story 2 — English Backward Compatibility (Priority: P1)

**Goal**: Existing configs without `nltk_language` field produce identical output to pre-change behavior.

**Independent Test**: Run existing test suite — all tests pass without modification. Existing `config.yaml` files work without changes.

### Tests for User Story 2

- [X] T012 [US1] [US2] Run existing full test suite `uv run poe test_unit` — verify 0 regressions in `tests/unit/indexing/operations/`
- [X] T013 [US1] [US2] Run `uv run poe check` — verify format + lint + typecheck pass

### Implementation for User Story 2

- [X] T014 [US2] Update `init_content.py` in `packages/graphrag/graphrag/config/init_content.py` to include `nltk_language: english` field in the `chunking` section with doc comment
- [X] T015 [US2] Verify `GraphRagConfig.chunking` in `packages/graphrag/graphrag/config/models/graph_rag_config.py` passes `nltk_language` through to `ChunkingConfig`

**Checkpoint**: At this point, User Stories 1 AND 2 are both complete — Russian chunking works AND existing configs are unchanged.

---

## Phase 5: User Story 3 — Other Language Support (Priority: P2)

**Goal**: Users can use sentence chunking for German, French, Spanish, and other supported NLTK PUNKT languages.

**Independent Test**: Set `nltk_language: german` (or french, spanish, etc.) and verify sentence splitting works.

### Tests for User Story 3

- [X] T016 [US3] Extend `test_sentence_chunker_nltk_language.py` with tests for `nltk_language="german"`, `nltk_language="french"` in `tests/unit/indexing/chunking/test_sentence_chunker_nltk_language.py`
- [X] T017 [US3] Test: invalid language code `nltk_language="invalid_xyz"` raises `LookupError` in `tests/unit/indexing/chunking/test_sentence_chunker_nltk_language.py`

### Implementation for User Story 3

- [X] T018 [US3] No additional code changes needed — `nltk.sent_tokenize(language=...)` already supports any language via `punkt_tab`

**Checkpoint**: All user stories are complete — multi-language support is functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, quickstart validation, and final checks

- [X] T019 [P] Update `packages/graphrag-chunking/README.md` with `nltk_language` field documentation
- [X] T020 [P] Update `docs/research/packages_todos.md` — mark P2 NLTK Multilingual Sentence Tokenizer as complete
- [X] T021 [P] Run quickstart.md validation — verify all config examples work
- [X] T022 [P] Add semversioner PATCH change entry: `uv run semversioner add-change -t patch -d "Add nltk_language config field to chunking for multilingual sentence tokenization."`
- [X] T023 [P] Run `uv run poe check` final validation — 0 errors
- [X] T024 [P] Run `uv run poe test` full test suite — 0 failures

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3–5)**: All depend on Foundational phase completion
  - US1 (Russian) can start after T004
  - US2 (English backward compat) can start after T010
  - US3 (Other languages) can start after US1 (shares implementation)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2 (T003–T004) — adds `nltk_language` parameter to `SentenceChunker`
- **US2 (P1)**: Starts after T010 (SentenceChunker modified) — adds config template update, runs regression tests
- **US3 (P2)**: Starts after US1 — no additional code changes, adds tests for other languages

### Within Each User Story

- Tests MUST be written and FAIL before implementation (Constitution Principle III)
- Models/config before services/chunkers
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- T005 (test file creation) can run in parallel with T006 (test implementation) — different task types, same file
- T019–T024 (Polish phase) are all [P] — can run in any order after all US phases
- T003 and T004 (Foundational) are [P] — different files, no cross-dependencies

---

## Parallel Example: Foundational Phase

```bash
# Launch both foundational tasks in parallel (different files):
Task: "Add nltk_language field to ChunkingConfig in chunking_config.py"
Task: "Add nltk_language to ChunkingDefaults in defaults.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T002)
2. Complete Phase 2: Foundational (T003–T004)
3. Complete Phase 3: US1 Russian chunking (T005–T011)
4. **STOP and VALIDATE**: Run `poe check` + `poe test_unit`
5. If passing, US1 MVP is ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready (T001–T004)
2. Add US1 Russian chunking → Test independently → MVP delivered (T005–T011)
3. Add US2 English backward compat → Run regression tests → Zero regression confirmed (T012–T015)
4. Add US3 Other languages → Run extended tests → All supported (T016–T018)
5. Polish → docs + semversioner + final check (T019–T024)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (Red-Green-Refactor)
- Commit after each task or logical group
- Constitution Principle III (Test-First) is NON-NEGOTIABLE
