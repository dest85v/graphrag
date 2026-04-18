---

description: "Task list for language-aware NLP factory implementation"
---

# Tasks: Language-Aware NLP Factory

**Input**: Design documents from `/specs/006-language-aware-nlp-factory/`
**Prerequisites**: plan.md, spec.md, data-model.md, research.md, quickstart.md

**Tests**: Test-First required by Constitution (Gate III). All test tasks MUST fail before implementation.

**Organization**: Tasks organized by user story. US1 and US2 are P1 and can be done in parallel after Foundational. US3 is P2.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story. Contains config changes and grammar extraction.

**⚠️ CRITICAL**: No user story implementation can begin until this phase is complete.

### Tests for Foundational (MUST FAIL first)

- [X] T001 [P] Create foundational test file in `tests/unit/test_noun_phrase_factory_language_field.py` with tests for: new `language` field on `TextAnalyzerConfig`, `language=None` default, `language="en"` default, `language="ru"` accepted, pydantic validation rejects invalid types

### Implementation

- [X] T002 [Found] Add `language: str | None` field to `TextAnalyzerConfig` in `packages/graphrag/graphrag/config/models/extract_graph_nlp_config.py` (FR-001)
- [X] T003 [Found] Rename `RU_NOUN_PHRASE_GRAMMARS` to `CFG_NOUN_PHRASE_GRAMMARS` in `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/cfg_extractor.py` (FR-008)
- [X] T004 [P] Extract `EN_NOUN_PHRASE_GRAMMARS` dict from `TextAnalyzerDefaults.noun_phrase_grammars` in `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/cfg_extractor.py` (FR-009)
- [X] T005 [P] Update `packages/graphrag/graphrag/config/defaults.py` to import `EN_NOUN_PHRASE_GRAMMARS` from `cfg_extractor.py` instead of hard-coding (FR-009)
- [X] T006 [P] Add `LANGUAGE_MODEL_MAP` dict to `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/factory.py`: `{"ru": "ru_core_news_md", "xx": "xx_ent_wiki_sm", default: "en_core_web_md"}` (FR-012)

**Checkpoint**: Foundational complete — `language` field added, grammars extracted, models mapped. All tests from T001 MUST pass before proceeding.

---

## Phase 2: User Story 1 — NLP-экстракция для русского текста (Priority: P1) 🎯 MVP

**Goal**: При `language: ru` автоматически выбираются `RU_STOP_WORDS` и `CFG_NOUN_PHRASE_GRAMMARS`, без ручного указания.

**Independent Test**: Запустить NLP-экстрактор на русском тексте с `language: ru` — проверить, что русские стоп-слова (`И`, `ИЛИ`, `ЧТО`) фильтруются из именных фраз, а английские (`stuff`, `thing`) — нет.

### Tests for User Story 1 (MUST FAIL first) ⚠️

- [X] T007 [P] [US1] Create `tests/unit/test_noun_phrase_factory_ru.py` with tests: `language="ru"` → `RU_STOP_WORDS` used; Russian stop words (`И`, `ИЛИ`, `ЧТО`) filtered from extracted noun phrases; `RU_STOP_WORDS` converted from frozenset to list in factory
- [X] T008 [P] [US1] Create `tests/unit/test_cfg_extractor_ru_grammars.py` with tests: `language="ru"` → `CFG_NOUN_PHRASE_GRAMMARS` used; `ADJ,NOUN` grammar applied to Russian POS tags; user grammars merge and override base `CFG_NOUN_PHRASE_GRAMMARS`

### Implementation for User Story 1

- [X] T009 [US1] Integrate `RU_STOP_WORDS` into `NounPhraseExtractorFactory.get_np_extractor()` — when `exclude_nouns is None` and `language == "ru"`, use `list(RU_STOP_WORDS)` in `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/factory.py` (FR-002)
- [X] T010 [US1] Integrate `CFG_NOUN_PHRASE_GRAMMARS` into CFG case of `get_np_extractor()` — when grammars empty and `language == "ru"`, use `CFG_NOUN_PHRASE_GRAMMARS` as base, then merge user grammars on top in `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/factory.py` (FR-005, FR-007)
- [X] T011 [P] [US1] Update `NounPhraseExtractorType.RegexEnglish` docstring in `packages/graphrag/graphrag/config/enums.py` to mention language limitation and recommend `syntactic_parser` for multilingual (FR-011)

**Checkpoint**: User Story 1 complete — `language: ru` selects `RU_STOP_WORDS` + `CFG_NOUN_PHRASE_GRAMMARS`. All T007, T008 tests MUST pass.

---

## Phase 3: User Story 2 — Backward compatibility для английских документов (Priority: P1)

**Goal**: При `language: null` или `language: en` поведение идентично текущему (EN_STOP_WORDS). Явный `exclude_nouns` переопределяет language-based выбор.

**Independent Test**: Запустить существующий английский конфиг без поля `language` — убедиться, что поведение идентично текущему. Запустить с `exclude_nouns: [...]` — убедиться, что пользовательские слова применяются.

### Tests for User Story 2 (MUST FAIL first) ⚠️

- [X] T012 [P] [US2] Add tests to `tests/unit/test_noun_phrase_factory_language_field.py`: `language=None` → `EN_STOP_WORDS`; `language="en"` → `EN_STOP_WORDS`; explicit `exclude_nouns` bypasses language-based selection; empty string `language=""` → `EN_STOP_WORDS` fallback
- [X] T013 [P] [US2] Add tests to `tests/unit/test_cfg_extractor_language_field.py`: `language=None` → `EN_NOUN_PHRASE_GRAMMARS`; `language="en"` → `EN_NOUN_PHRASE_GRAMMARS`; explicit `noun_phrase_grammars` bypasses base selection; user grammars merge and override `EN_NOUN_PHRASE_GRAMMARS`

### Implementation for User Story 2

- [X] T014 [US2] Ensure default case in factory uses `EN_STOP_WORDS` when `language` is `None`, `"en"`, or empty string in `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/factory.py` (FR-003, FR-004)
- [X] T015 [US2] Ensure CFG default case uses `EN_NOUN_PHRASE_GRAMMARS` when `language` is `None`, `"en"`, or empty string in `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/factory.py` (FR-006)
- [X] T016 [P] [US2] Add `language: en` field description to init config template in `packages/graphrag/graphrag/config/init_content.py` (FR-010)

**Checkpoint**: User Story 2 complete — backward compatibility verified, user overrides work. All T012, T013 tests MUST pass.

---

## Phase 4: User Story 3 — Автовыбор spaCy-модели по языку (Priority: P2)

**Goal**: Пользователь указывает `language: ru` без `model_name` — система автоматически выбирает `ru_core_news_md`.

**Independent Test**: Установить `language: ru` без `nlp_model` и `model_name` — проверить, что `effective_model_name` = `ru_core_news_md`.

### Tests for User Story 3 (MUST FAIL first) ⚠️

- [X] T017 [P] [US3] Create `tests/unit/test_nlp_model_auto_select.py` with tests: `language="ru"` → `ru_core_news_md`; `language="de"` → `de_core_news_md`; `language="xx"` → `xx_ent_wiki_sm`; explicit `nlp_model` overrides auto-selection; `language=None` → `en_core_web_md`

### Implementation for User Story 3

- [X] T018 [US3] Implement auto spaCy model selection in `get_np_extractor()`: when both `nlp_model` and `model_name` are `None`, resolve via `LANGUAGE_MODEL_MAP[language]` with `"en_core_web_md"` fallback in `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/factory.py` (FR-012)

**Checkpoint**: User Story 3 complete — spaCy model auto-selected from language. All T017 tests MUST pass.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Validation, documentation, and release readiness.

- [X] T019 Run `uv run poe check` — verify format + lint + typecheck pass with 0 errors
- [X] T020 Run `uv run poe test_unit` — verify all existing unit tests pass (0 regressions, SC-004)
- [X] T021 [P] Update `docs/research/packages_todos.md` — mark P1 Language-Aware NLP Factory as completed
- [X] T022 [P] Update `README_RU.md` — add `language` field documentation and auto-spaCy model selection
- [X] T023 Run `uv run semversioner add-change -t minor -d "Add language-aware NLP factory with auto stop words and CFG grammars selection."` (Constitution Gate V)
- [X] T024 Validate quickstart examples by applying them to a test config and verifying factory behavior

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 1)**: No dependencies — starts immediately
- **US1 (Phase 2)**: Depends on Foundational — NO dependency on US2
- **US2 (Phase 3)**: Depends on Foundational — NO dependency on US1 (can run in parallel)
- **US3 (Phase 4)**: Depends on Foundational — NO dependency on US1/US2
- **Polish (Phase 5)**: Depends on all desired stories being complete

### User Story Dependencies

- **US1 (P1)**: After Foundational — no dependency on US2 or US3
- **US2 (P1)**: After Foundational — no dependency on US1 or US3 (parallel with US1)
- **US3 (P2)**: After Foundational — no dependency on US1 or US2

### Within Each User Story

- Tests MUST be written and FAIL before implementation (Constitution Gate III)
- Tests before implementation tasks
- Story complete before moving to next

### Parallel Opportunities

- T001 (foundational test) — parallel with T004, T005, T006 (implementation)
- T004, T005, T006 — all different files, fully parallel
- T007, T008 — US1 tests, parallel
- T010, T011 — US1 implementation, parallel (different files)
- T012, T013 — US2 tests, parallel
- T016 — US2 implementation, independent of T014, T015
- US1 and US2 can proceed in parallel (both P1, both depend only on Foundational)
- T017 — US3 test, independent of US1/US2
- T021, T022 — polish, parallel

---

## Parallel Example: Foundational Phase

```bash
# All foundational tests + implementation can launch together:
Task: "Create foundational test file in tests/unit/test_noun_phrase_factory_language_field.py"
Task: "Add language field to TextAnalyzerConfig in extract_graph_nlp_config.py"
Task: "Rename RU_NOUN_PHRASE_GRAMMARS to CFG_NOUN_PHRASE_GRAMMARS in cfg_extractor.py"
Task: "Extract EN_NOUN_PHRASE_GRAMMARS from defaults.py into cfg_extractor.py"
Task: "Update defaults.py to import EN_NOUN_PHRASE_GRAMMARS"
Task: "Add LANGUAGE_MODEL_MAP dict to factory.py"
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Foundational (Phase 1)
2. Complete US1 (Phase 2) — Russian stop words + CFG grammars
3. **STOP and VALIDATE**: Run T007, T008 — all pass
4. Run `poe check` — 0 errors
5. MVP delivered: Russian language support with auto stop words and grammars

### Incremental Delivery

1. Foundational → base infrastructure ready
2. US1 → Russian stop words + grammars (MVP!)
3. US2 → Backward compatibility (P1, can be done with US1 in parallel)
4. US3 → Auto spaCy model (P2)
5. Polish → validation + semversioner + docs

### Parallel Team Strategy

With multiple developers:
1. Team completes Foundational together
2. Developer A: US1 (Russian support)
3. Developer B: US2 (Backward compat)
4. After both done: Developer A or B: US3 (Auto model)

---

## Notes

- Total tasks: 24
- US1 (P1): 5 tasks (2 tests + 3 implementation)
- US2 (P1): 5 tasks (2 tests + 3 implementation)
- US3 (P2): 2 tasks (1 test + 1 implementation)
- Polish: 6 tasks
- All tests are mandatory per Constitution Gate III (Test-First)
- All tests MUST fail before implementation starts
- Commit after each task or logical group
- Verify `poe check` passes after Phase 5
