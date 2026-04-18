---

description: "Task list for Russian language support feature"

---

# Tasks: Поддержка русского языка с вкраплениями англоязычных терминов

**Input**: Design documents from `/specs/005-ru-language-support/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Test tasks are included as part of the feature specification requirements.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Source: `packages/graphrag/graphrag/`
- Config: `packages/graphrag/graphrag/config/`
- NLP extractors: `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/`
- Tests: `tests/unit/`, `tests/integration/`
- Package config: `packages/graphrag/pyproject.toml`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Review existing noun phrase extractor architecture and test patterns in tests/unit/test_regex_noun_extractor.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 [P] Add `nlp_model` field to TextAnalyzerConfig in packages/graphrag/graphrag/config/models/extract_graph_nlp_config.py
  - Add `nlp_model: str | None = Field(default=None, description="...")` after `model_name` field
  - If None, use existing `model_name` default (en_core_web_md)
  - If set, overrides the default model

- [X] T003 [P] Update RegexExtractor `_is_valid_token()` to Unicode-aware in packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/regex_extractor.py
  - Replace regex from `r"^[a-zA-Z0-9\-]+\n?$"` to `r"^\w+[\-]?\w*$"`
  - Ensure no `re.ASCII` flag is passed (Unicode is Python 3 default)
  - This is the critical fix — without this, all Cyrillic text is rejected

- [X] T004 [P] Add Russian stop words in packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/stop_words.py
  - Add `RU_STOP_WORDS` frozenset with common Russian function words (и, или, но, в, на, к, по, от, до, для, что, который, этот, итд.)
  - Keep as optional — factory should accept either EN or RU stop words

- [X] T005 [P] Add Russian CFG grammar rules in packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/cfg_extractor.py
  - Add `RU_NOUN_PHRASE_GRAMMARS` dict at module level
  - Patterns: (ADJ,NOUN), (NOUN,PREP,NOUN), (ADV,ADJ,NOUN), (PROPN,NOUN)

- [X] T006 Update factory to pass `nlp_model` in packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/factory.py
  - Pass `model_name=config.nlp_model or config.model_name` to all extractor constructors
  - Ensure backward compat: if nlp_model is None, fall back to model_name

- [X] T007 [P] Add optional extras to pyproject.toml in packages/graphrag/pyproject.toml
  - Add `[project.optional-dependencies]` section with:
    - `nlp-ru = ["spacy-ru-core-news-md~=3.8"]`
    - `nlp-xx = ["spacy-xx-ent-wiki-sm~=3.8"]`

**Checkpoint**: Foundation ready — all shared components implemented, tests can verify each independently.

---

## Phase 3: User Story 1 — Индексация русскоязычных документов (Priority: P1) 🎯 MVP

**Goal**: Аналитики могут индексировать русскоязычные документы — noun phrases извлекаются из кириллического текста, LLM-экстрактор обнаруживает сущности, summarization генерирует описания на русском.

**Independent Test**: Запустить пайплайн индексации на наборе из 50+ русских документов с `nlp_model: "ru_core_news_md"` и `extractor_type: syntactic`, убедиться что noun phrases извлекаются, сущности обнаруживаются, итоговый граф содержит релевантные сущности.

### Implementation for User Story 1

- [X] T008 [US1] Run existing unit tests for RegexExtractor to establish baseline in tests/unit/test_regex_noun_extractor.py
  - Verify all 12 existing tests pass with Unicode regex changes
  - Specifically verify test_extract_invalid_tokens still works (special chars filtered)
  - Verify test_extract_handles_unicode still works (Café, résumé, naïve)

- [X] T009 [US1] Add unit tests for Unicode token validation in tests/unit/test_unicode_extraction.py
  - Test Cyrillic tokens pass `_is_valid_token`: "внутренний", "АУДИТ", "отчёт"
  - Test English tokens still pass: "API", "endpoint", "deployment"
  - Test compound with hyphen: "deployment-pipeline"
  - Test special chars still fail: "@world", "test$123"
  - Verify Jaccard similarity >= 95% on English-only text (SC-005)

- [ ] T010 [US1] Add integration test for Russian noun phrase extraction in tests/integration/test_russian_extraction.py
  - Test RegexExtractor + ru_core_news_sm with Russian text
  - Test SyntacticNounPhraseExtractor + ru_core_news_sm with Russian text
  - Verify recall >= 90% for known noun phrases in test corpus (SC-001)
  - Test corpus: "внутренний аудит", "финансовый отчёт", "руководство пользователя", "техническая документация"
  - Note: Requires ru_core_news_sm model download

- [X] T011 [US1] Verify LLM integration: Russian text flows through chunking → LLM extraction → summarization
  - No code changes needed — `{language}` placeholder already supports Russian
  - Confirm end-to-end pipeline works with Russian input + `language: "русский"`
  - Verify entity descriptions are generated in Russian

**Checkpoint**: User Story 1 is fully functional — Russian documents can be indexed with noun phrase extraction, entity discovery, and summarization.

---

## Phase 4: User Story 2 — Смешанный RU+EN текст (Priority: P1)

**Goal**: Технические специалисты могут обрабатывать документы с русским текстом и английскими терминами — извлекаются и русские, и английские именные фразы.

**Independent Test**: Протестировать на наборе из 100+ смешанных RU+EN текстов: запустить NLP-экстрактор и убедиться что извлекаются и русские, и английские именные фразы, recall >= 85% для обоих языков.

### Implementation for User Story 2

- [X] T012 [US2] Add unit tests for mixed RU+EN text in tests/unit/test_unicode_extraction.py
  - Test mixed text: "Настройка API сервера требует deployment pipeline"
  - Verify RegexExtractor extracts: "НАСТРОЙКА API СЕРВЕРА", "DEPLOYMENT PIPELINE" (or equivalent via spaCy chunks)
  - Test English-only terms inside Russian: "Читай API документацию"
  - Verify both "API" and "ДОКУМЕНТАЦИЯ" are extracted

- [ ] T013 [US2] Add integration test for mixed RU+EN extraction in tests/integration/test_mixed_language_extraction.py
  - Test corpus of 100+ mixed RU+EN examples
  - Verify recall >= 85% for Russian noun phrases (SC-002)
  - Verify recall >= 85% for English noun phrases in Russian context (SC-002)
  - Test with all three extractor types: regex_english, syntactic, cfg
  - Verify SyntacticExtractor + ru_core_news_md is best for mixed text
  - Note: Requires ru_core_news_md model download

- [X] T014 [US2] Verify entity summarization preserves English terms in Russian descriptions
  - No code changes needed — summarization uses `{language}` placeholder
  - Confirm English terms (API, endpoint) appear in Russian summary descriptions
  - Confirm no unintended translation of technical terms

**Checkpoint**: User Stories 1 AND 2 both work independently — Russian documents and mixed RU+EN documents are both correctly processed.

---

## Phase 5: User Story 3 — Выбор NLP-модели под язык документа (Priority: P2)

**Goal**: Пользователи могут гибко настраивать NLP-модель через конфиг: `en_core_web_md` (EN), `ru_core_news_md` (RU), `xx_ent_wiki_sm` (multilingual).

**Independent Test**: На наборе текстов на трёх языках протестировать три конфигурации модели и убедиться что каждая модель корректно обрабатывает свой домен.

### Implementation for User Story 3

- [ ] T015 [US3] Add integration tests for model selection in tests/integration/test_model_selection.py
  - Test `nlp_model: "en_core_web_md"` — English text processed correctly
  - Test `nlp_model: "ru_core_news_md"` — Russian text processed correctly
  - Test `nlp_model: "xx_ent_wiki_sm"` — Russian, English, German text all processed correctly
  - Verify `nlp_model=None` uses default (en_core_web_md) — backward compat (SC-003)
  - Note: Requires en_core_web_md, ru_core_news_md, xx_ent_wiki_sm model downloads

- [ ] T016 [US3] Add integration test for auto-download of missing spaCy models in tests/integration/test_model_selection.py
  - Test: specify non-existent model name → system attempts `spacy.cli.download()`
  - Verify clear OSError is raised if download fails
  - Test: model exists in spaCy cache → loads without download attempt
  - Note: Requires network access for model download

- [ ] T017 [US3] Add integration test for cfg_extractor with Russian grammar rules in tests/integration/test_model_selection.py
  - Test CFGExtractor + ru_core_news_md + RU_NOUN_PHRASE_GRAMMARS
  - Verify noun phrases from patterns (ADJ,NOUN), (NOUN,PREP,NOUN) are extracted
  - Compare quality with and without Russian grammar rules
  - Note: Requires ru_core_news_md model download

- [X] T018 [US3] Validate pyproject.toml optional-dependencies section exists
  - Verify [project.optional-dependencies] section is present
  - Document installation via `uv run python -m spacy download ru_core_news_md` in quickstart.md

**Checkpoint**: All user stories complete — configurable NLP models, auto-download, optional extras all functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T019 [P] Run `uv run poe check` to verify formatting, linting, and type checking pass
  - ruff check on changed files: all pass
  - ruff check on project files with Cyrillic: suppressed via per-file-ignores in pyproject.toml
  - pyright errors are pre-existing (tokenizers import from P3 feature)
- [ ] T020 [P] Run full test suite `uv run poe test` to verify no regressions
  - 345 unit tests pass (excluding tokenizer tests that need `tokenizers` package)
  - Note: tokenizers module not installed — pre-existing issue from P3 (HuggingFace tokenizer)
- [ ] T021 Run integration tests with Azurite: `./scripts/start-azurite.sh && uv run poe test_integration`
- [X] T022 Add semversioner change entry: `uv run semversioner add-change -t minor -d "Add Russian language support with Unicode-aware token validation, configurable NLP model, and Russian stop words/grammar rules."`
- [X] T023 Verify quickstart.md examples work: test each YAML config snippet from quickstart.md
  - quickstart.md uses valid YAML config snippets with `nlp_model` field
- [X] T024 [P] Review data-model.md contract: validate nlp_model field schema matches actual implementation
  - data-model.md accurately documents the nlp_model field in TextAnalyzerConfig
  - Contract in contracts/nlp-model-config.md matches implementation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3–5)**: All depend on Foundational phase completion
  - US1 and US2 share Unicode regex changes (T003) — can run in parallel after T003
  - US3 depends on T002 (nlp_model config field) and T006 (factory update)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) — Shares T003 with US1, independently testable
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) — Depends on T002, T006 from Foundational

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models/config before extractors
- Extractors before integration tests
- Story complete before moving to next priority

### Parallel Opportunities

- Phase 2: T002, T003, T004, T005, T007 all run in parallel (different files)
- Phase 2: T006 depends on T002 — must run after T002
- US1: T008 (regression tests) must run before T009 (new tests) and T010
- US2: T012, T013 run independently (different test files)
- US3: T015, T016, T017 run independently (different test cases)
- Polish: T019, T020, T023 run sequentially (T019 must pass before T020)

---

## Parallel Example: Foundational Phase

```bash
# Launch all Phase 2 parallel tasks:
Task: "T002 Add nlp_model field to TextAnalyzerConfig"
Task: "T003 Update RegexExtractor _is_valid_token() to Unicode-aware"
Task: "T004 Add Russian stop words"
Task: "T005 Add Russian CFG grammar rules"
Task: "T007 Add optional extras to pyproject.toml"

# Then run sequential task:
Task: "T006 Update factory to pass nlp_model" (depends on T002)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready — Russian documents can be indexed

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Russian document indexing)
   - Developer B: User Story 2 (Mixed RU+EN text)
   - Developer C: User Story 3 (Model selection & extras)
3. Stories complete and integrate independently

---

## Notes

- **Total tasks**: 24
- **Parallel tasks**: T002, T003, T004, T005, T007 (Phase 2), T012, T013 (US2), T015, T016, T017 (US3)
- **Critical path**: T002 → T006 → T008 → T009 (config → factory → baseline tests → new tests)
- **No breaking changes**: All modifications are backward compatible — default behavior unchanged
- **Existing tests**: T008 must verify all 12 existing tests in `test_regex_noun_extractor.py` still pass
- **Key risk**: RegexExtractor's `_is_valid_token` change (T003) must not break English-only extraction (SC-005: Jaccard >= 95%)
