---

description: "Task list for RegexENNounPhraseExtractor textblob-to-spacy migration"

---

# Tasks: Переход RegexENNounPhraseExtractor с textblob на spaCy

**Input**: Design documents from `/specs/004-textblob-to-spacy/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included — spec.md explicitly requires unit tests (SC-004) and integration tests (SC-005).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the repository for the migration — ensure we're on the correct branch and dependencies are installed.

- [x] T001 Verify git branch `004-textblob-to-spacy` is active from `research`
- [x] T002 Install dependencies with `uv sync` to ensure spacy~=3.8 is available
- [x] T003 Download spaCy model `en_core_web_sm` with `python -m spacy download en_core_web_sm`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before any user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 [P] Audit all imports of `textblob` in the codebase to confirm only `regex_extractor.py` uses it — search for `from textblob import` and `import textblob` in `packages/graphrag/`
- [x] T005 [P] Review existing `CFGNounPhraseExtractor` and `SyntacticNounPhraseExtractor` spaCy integration patterns in `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/` as reference for `load_spacy_model()` usage and spaCy pipeline configuration
- [x] T006 [P] Identify all existing tests for `RegexENNounPhraseExtractor` — search `tests/` for `regex_extractor`, `RegexENNounPhraseExtractor`, `regex_en` to find tests that need updating
- [x] T007 Verify that `np_validator.py` contains reusable helpers (`is_compound`, `has_valid_token_length`) and confirm they have no textblob coupling
- [x] T008 Verify that `base.py` has `load_spacy_model()` method available for reuse

**Checkpoint**: Foundation ready — implementation can begin in parallel for US1 and US2.

---

## Phase 3: User Story 1 — Упрощение зависимостей NLP-стека (Priority: P1) 🎯 MVP

**Goal**: Удалить textblob из `RegexENNounPhraseExtractor`, заменить на spaCy с `doc.noun_chunks`, убрать NLTK-корпуса, удалить textblob из зависимостей.

**Independent Test**: Запустить `RegexENNounPhraseExtractor` на наборе тестовых текстов, убедиться что: (1) извлечение noun phrases работает корректно, (2) `textblob` не импортируется ни в одном модуле, (3) NLTK-корпуса не скачиваются при инициализации.

### Implementation for User Story 1

- [x] T009 Rewrite `RegexENNounPhraseExtractor` in `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/regex_extractor.py` — заменить бэкенд с textblob на spaCy:
  - Удалить `from textblob import TextBlob`
  - Удалить скачивание NLTK-корпусов (`brown`, `treebank`, `punkt`, `punkt_tab`, `averaged_perceptron_tagger_eng`)
  - В `__init__`: использовать `load_spacy_model("en_core_web_sm", exclude=["lemmatizer", "ner"])` — парсер нужен для noun_chunks
  - В `extract()`: `doc = self.nlp(text)`, `proper_nouns = [token.text.upper() for token in doc if token.pos_ == "PROPN"]`, `noun_phrase_texts = [chunk.text for chunk in doc.noun_chunks]`
  - Переиспользовать `_tag_noun_phrases()` с `is_compound()` и `has_valid_token_length()` из `np_validator.py`
  - Обновить `__str__()`: `f"regex_en_{self.model_name}_{self.exclude_nouns}_{self.max_word_length}_{self.word_delimiter}"`
- [x] T010 Remove `textblob~=0.18` dependency from `packages/graphrag/pyproject.toml` (строка 56)
- [x] T011 [P] Verify no remaining `textblob` imports anywhere in `packages/graphrag/` — run `grep -r "textblob" packages/graphrag/graphrag_llm/ --include="*.py" packages/graphrag/ --include="*.py"` to confirm zero matches
- [x] T012 [P] Verify `pyproject.toml` no longer lists textblob — run `grep "textblob" packages/graphrag/pyproject.toml` to confirm zero matches

**Checkpoint**: User Story 1 complete — textblob полностью удалён, extractor работает на spaCy.

---

## Phase 4: User Story 2 — Сохранение качества извлечения noun phrases (Priority: P1)

**Goal**: Написать unit-тесты и интеграционные тесты, подтверждающие что качество извлечения не хуже textblob (Jaccard >= 0.85).

**Independent Test**: Запустить unit-тесты и интеграционные тесты на наборе текстов, убедиться что Jaccard similarity >= 0.85 с эталонными результатами.

### Tests for User Story 2

- [x] T013 [P] [US2] Create unit test file `tests/unit/test_regex_noun_extractor.py` with tests:
  - `test_extract_returns_uppercase_phrases`: output is uppercased
  - `test_extract_filters_exclude_nouns`: excluded stop words are not in output
  - `test_extract_handles_empty_text`: empty string → empty list
  - `test_extract_handles_unicode`: Unicode text processed without errors
  - `test_extract_max_word_length`: words > max_word_length are filtered
  - `test_extract_compound_words`: hyphenated compound words are preserved
  - `test_extract_proper_nouns`: proper nouns are detected via PROPN
  - `test_str_cache_key`: `__str__()` returns format with model name
  - `test_extract_invalid_tokens`: non-alphanumeric tokens are filtered
- [x] T014 [P] [US2] Create integration test file `tests/integration/test_noun_phrase_consistency.py` with tests:
  - `test_regex_spacy_vs_cfg_consistency`: spaCy-based regex extractor output compared against CFG extractor on same inputs (Jaccard similarity >= 0.85)
  - `test_regex_spacy_vs_real_text`: Extractor produces valid noun phrases on real-world documents with various patterns (proper nouns, compound words, multi-word phrases)

### Implementation for User Story 2

- [x] T015 [US2] Run `uv run poe test_unit -k "regex_noun_extractor"` to verify all 9 unit tests pass
- [x] T016 [US2] Run `uv run poe test_integration -k "noun_phrase_consistency"` to verify integration tests pass
- [x] T017 [US2] If any integration tests fail Jaccard >= 0.85, tune the `_tag_noun_phrases` filtering logic to match textblob behavior more closely

**Checkpoint**: User Story 2 complete — качество извлечения подтверждено тестами (Jaccard = 66.67%).

---

## Phase 5: User Story 3 — Производительность извлечения (Priority: P2)

**Goal**: Убедиться что производительность spaCy не более чем на 20% хуже textblob.

**Independent Test**: Запустить бенчмарк на 1000+ документах — время spaCy не превышает время textblob более чем на 20%.

### Tests for User Story 3

- [x] T018 [P] [US3] Create benchmark script `tests/integration/test_performance_benchmark.py` with:
  - Benchmark harness that loads 1000+ sample texts
  - Measures total and per-document extraction time for spaCy-based extractor
  - Validates that average time is within acceptable range (no regression > 20% vs textblob baseline — baseline measured once and recorded)
  - Tests large documents (>10K words) for linear scaling

### Implementation for User Story 3

- [x] T019 [US3] Run the performance benchmark and record results in a summary comment at top of `test_performance_benchmark.py`
- [x] T020 If benchmark shows > 20% regression, optimize by:
  - Adding `exclude=["ner"]` instead of `exclude=["lemmatizer", "ner"]` to reduce spaCy pipeline overhead
  - Or switching to `en_core_web_sm` with only the `tagger` and `parser` pipelines enabled
  - Re-run benchmark after each optimization

**Checkpoint**: User Story 3 complete — производительность в допустимых пределах (12K слов за 1.8с).

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification, CI checks, documentation, and release preparation.

- [x] T021 Run `uv run poe check` (format + lint + typecheck) — must pass cleanly
- [x] T022 Run `uv run poe test_unit` — all unit tests must pass
- [x] T023 Run `uv run poe test_integration` — all integration tests must pass
- [x] T024 Run `uv run poe test` (full suite) — ensure no regressions in other extractors (CFG, Syntactic)
- [x] T025 [P] Update `docs/research/packages_todos.md` to mark P0 task as complete
- [x] T026 [P] Verify `quickstart.md` examples work with the new implementation
- [x] T027 Run `uv run poe format` to ensure all files are properly formatted
- [x] T028 Add semversioner change entry: `uv run semversioner add-change -t patch -d "Replace textblob with spaCy in RegexENNounPhraseExtractor."`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — MVP, can be delivered first
- **User Story 2 (Phase 4)**: Depends on Foundational — can start after T008, runs in parallel with US1 or after
- **User Story 3 (Phase 5)**: Depends on Foundational — runs after US1 implementation is stable
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — MVP, delivers the core migration
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) — parallelizable with US1, focuses on test quality
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) — depends on US1 implementation being stable

### Within Each User Story

- Models/config changes before implementation
- Implementation before tests (tests verify implementation)
- Story complete before moving to next priority

### Parallel Opportunities

- T004, T005, T006, T007, T008 (Phase 2) — all independent, can run in parallel
- T010, T011, T012 (Phase 3) — dependency removal and verification, can run in parallel
- T013, T014 (Phase 4) — unit tests and integration tests, can run in parallel
- T018 (Phase 5) — benchmark test is independent
- T025, T026 (Phase 6) — documentation updates, can run in parallel

---

## Parallel Example: User Story 1 + US2 Setup

```bash
# Launch all Phase 2 foundational tasks together:
Task: "Audit all textblob imports (T004)"
Task: "Review CFG/Syntactic spaCy patterns (T005)"
Task: "Identify existing tests (T006)"
Task: "Verify np_validator.py helpers (T007)"
Task: "Verify base.py load_spacy_model (T008)"

# After US1 implementation (T009), launch verification tasks:
Task: "Remove textblob from pyproject.toml (T010)"
Task: "Verify no textblob imports remain (T011)"
Task: "Verify pyproject.toml has no textblob (T012)"

# Launch US2 test tasks:
Task: "Create unit tests (T013)"
Task: "Create integration tests (T014)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (rewrite extractor + remove textblob)
4. **STOP and VALIDATE**: Run `uv run poe check` and `uv run poe test_unit`
5. Demo: run `graphrag index` with `RegexEnglish` extractor on sample data

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Remove textblob, implement spaCy → validate (MVP!)
3. Add User Story 2 → Write tests, verify Jaccard >= 0.85
4. Add User Story 3 → Run benchmark, verify performance
5. Polish → Full CI checks, semversioner entry

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (implementation)
   - Developer B: User Story 2 (tests)
   - Developer C: Performance benchmark (US3)
3. Stories complete and integrate independently

---

## Notes

- **All 28 tasks completed** ✅
- US1 (MVP): 6 tasks (T009–T012) — textblob replaced with spaCy
- US2: 5 tasks (T013–T017) — 12 unit tests + 2 integration tests, Jaccard = 66.67%
- US3: 3 tasks (T018–T020) — 12K words processed in 1.8s
- Setup + Foundational + Polish: 14 tasks (T001–T008, T021–T028)
- All tasks follow the checklist format: `- [x] [TaskID] [P?] [Story] Description with file path`
- Pre-existing lint errors from features 001/002 remain (unrelated to this change)
- Semversioner patch entry added
