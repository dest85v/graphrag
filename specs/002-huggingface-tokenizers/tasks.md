# Tasks: Add HuggingFace Tokenizers for Non-OpenAI Models

**Input**: Design documents from `/specs/002-huggingface-tokenizers/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — test-first approach per Constitution principle III.

**Organization**: Tasks organized by user story (US1, US2, US3) for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add optional dependency extra to the package configuration.

- [x] T001 Add `huggingface` optional dependency extra (`tokenizers>=0.21,<0.23`, `sentencepiece>=0.2,<0.3`, `protobuf>=5.0,<6.0`) to `packages/graphrag-llm/pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core types and config changes that MUST be complete before any user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T002 Add `HuggingFace = "huggingface"` to `TokenizerType` enum in `packages/graphrag-llm/graphrag_llm/config/types.py`
- [x] T003 Add `model_id` field to `TokenizerConfig` (str | None, with description for HuggingFace model ID) in `packages/graphrag-llm/graphrag_llm/config/tokenizer_config.py`
- [x] T004 Add `_validate_huggingface_config()` method to `TokenizerConfig` that requires non-empty `model_id` when `type == "huggingface"`, update `@model_validator` to call it; keep existing Tiktoken validation
- [x] T005 [P] Add unit tests for `TokenizerType.HuggingFace` enum value in `tests/unit/tokenizer/test_tokenizer_types.py`
- [x] T006 [P] Add unit tests for `TokenizerConfig` validation — `huggingface` type with valid `model_id`, with empty `model_id` (should raise), with missing `model_id` (should raise) in `tests/unit/config/test_tokenizer_config.py`

**Checkpoint**: Foundation ready — US1 can now begin (enum + config are defined and validated).

---

## Phase 3: User Story 1 — Tokenize text for any LLM model (Priority: P1) 🎯 MVP

**Goal**: Provide a working `HuggingFaceTokenizer` that correctly encodes/decodes text for any HuggingFace model, supporting both Hub downloads and local `tokenizer.json` files.

**Independent Test**: Configure a model with `tokenizer.type = "huggingface"` and `tokenizer.model_id = "meta-llama/Llama-3.1-8B-Instruct"`. Call `create_tokenizer()` and verify `encode()`/`decode()`/`num_tokens()` produce correct results. Compare token counts against `transformers.AutoTokenizer` for the same text.

### Tests for User Story 1 ⚠️

> **Write these tests FIRST, ensure they FAIL before implementation**

- [x] T007 [P] [US1] Unit test: `HuggingFaceTokenizer.encode()` produces valid integer token IDs for Llama 3 text in `tests/unit/tokenizer/test_huggingface_tokenizer.py`
- [x] T008 [P] [US1] Unit test: `HuggingFaceTokenizer.decode()` round-trips correctly (decode(encode(text)) ≈ text) in `tests/unit/tokenizer/test_huggingface_tokenizer.py`
- [x] T009 [P] [US1] Unit test: `HuggingFaceTokenizer.num_tokens()` returns `len(encode(text))` in `tests/unit/tokenizer/test_huggingface_tokenizer.py`
- [x] T010 [P] [US1] Unit test: `HuggingFaceTokenizer` loads from local `tokenizer.json` file path in `tests/unit/tokenizer/test_huggingface_tokenizer_local.py`
- [x] T011 [US1] Unit test: `create_tokenizer()` with `TokenizerConfig(type="huggingface", model_id=...)` returns a `HuggingFaceTokenizer` instance in `tests/unit/tokenizer/test_tokenizer_factory.py`

### Implementation for User Story 1

- [x] T012 [US1] Create `HuggingFaceTokenizer` class in `packages/graphrag-llm/graphrag_llm/tokenizer/huggingface_tokenizer.py` — implements `Tokenizer` ABC with `encode()`, `decode()`, `num_tokens()`, `num_prompt_tokens()` using `tokenizers.Tokenizer.from_pretrained()` or `from_file()`, with `add_special_tokens=False`
- [x] T013 [US1] Register `HuggingFaceTokenizer` in `TokenizerFactory` — add `case TokenizerType.HuggingFace:` branch in `create_tokenizer()` in `packages/graphrag-llm/graphrag_llm/tokenizer/tokenizer_factory.py`
- [x] T014 [US1] Add `HuggingFaceTokenizer` to `__all__` in `packages/graphrag-llm/graphrag_llm/tokenizer/__init__.py`

**Checkpoint**: At this point, US1 is fully functional — a HuggingFace-backed tokenizer can be created and used for encode/decode/token counting.

---

## Phase 4: User Story 2 — Automatic tokenizer selection based on model family (Priority: P1)

**Goal**: `get_tokenizer()` automatically routes OpenAI models to tiktoken and all other models to the HuggingFace tokenizer, with a safe fallback for unknown models.

**Independent Test**: Configure a completion model with `model = "gpt-4o"` — verify `get_tokenizer()` returns an `OpenAITokenizer`. Configure `model = "meta-llama/Llama-3.1-8B-Instruct"` — verify it returns a `HuggingFaceTokenizer`. Configure `model = "unknown-model"` — verify it falls back to `OpenAITokenizer`.

### Tests for User Story 2 ⚠️

- [x] T015 [P] [US2] Integration test: `get_tokenizer()` returns `OpenAITokenizer` for OpenAI model names (gpt-4o, gpt-3.5-turbo, text-embedding-3-large) in `tests/unit/test_tokenizer_routing.py`
- [x] T016 [P] [US2] Integration test: `get_tokenizer()` returns `HuggingFaceTokenizer` for non-OpenAI model names (Llama, Mistral, Qwen) in `tests/unit/test_tokenizer_routing.py`
- [x] T017 [US2] Integration test: `get_tokenizer()` falls back to `OpenAITokenizer` with `cl100k_base` for unknown model names in `tests/unit/test_tokenizer_routing.py`

### Implementation for User Story 2

- [x] T018 [US2] Implement `_OPENAI_MODEL_PATTERNS` set and routing logic in `get_tokenizer()` in `packages/graphrag/graphrag/tokenizer/get_tokenizer.py` — OpenAI patterns → `TokenizerType.Tiktoken`, else → `TokenizerType.HuggingFace`
- [x] T019 [US2] Update fallback path in `get_tokenizer()` when `model_config is None` to still use `TokenizerType.Tiktoken` with `ENCODING_MODEL` (no behavioral change, verify no regression)

**Checkpoint**: US2 is complete — tokenizer selection is automatic based on model name.

---

## Phase 5: User Story 3 — Consistent token counting across all tokenizer backends (Priority: P2)

**Goal**: Ensure token counting is accurate and consistent across all backends, with proper error handling for edge cases (Hub unreachable, SentencePiece missing).

**Independent Test**: Compare `HuggingFaceTokenizer.num_tokens(text)` against `transformers.AutoTokenizer` for 100 diverse texts across Llama, Mistral, Qwen, and Gemma. Verify match rate ≥ 99%. Test error handling for unreachable Hub and missing sentencepiece.

### Tests for User Story 3 ⚠️

- [x] T020 [P] [US3] Integration test: token count consistency — `HuggingFaceTokenizer.num_tokens(text)` matches `transformers.AutoTokenizer` for diverse texts in `tests/integration/test_tokenizer_consistency.py`
- [x] T021 [P] [US3] Unit test: `HuggingFaceTokenizer` handles UTF-8 text with emojis and non-ASCII characters without errors in `tests/unit/tokenizer/test_huggingface_tokenizer.py`
- [x] T022 [US3] Unit test: `HuggingFaceTokenizer.num_prompt_tokens()` handles both string and list-of-dict messages in `tests/unit/tokenizer/test_huggingface_tokenizer.py`

### Implementation for User Story 3

- [x] T023 [US3] Add error handling in `HuggingFaceTokenizer` for Hub-unreachable scenarios — catch `OSError`/`ValueError` from `from_pretrained()` and re-raise with clear message including fallback guidance (use local `tokenizer.json`) in `packages/graphrag-llm/graphrag_llm/tokenizer/huggingface_tokenizer.py`
- [x] T024 [US3] Verify `num_prompt_tokens()` implementation in `HuggingFaceTokenizer` inherits from `Tokenizer` base class correctly (no override needed — ABC default implementation uses `num_tokens()` which is already implemented)
- [x] T025 [US3] Add documentation comment in `HuggingFaceTokenizer.__init__()` explaining `add_special_tokens=False` rationale for tiktoken consistency

**Checkpoint**: US3 is complete — token counting is consistent and edge cases are handled.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, backward compatibility verification, and final cleanup.

- [x] T026 [P] Verify all existing unit tests for `OpenAITokenizer` and `TiktokenTokenizer` still pass — no regressions in `packages/graphrag-llm/tests/unit/`
- [x] T027 [P] Verify all existing integration tests still pass — no regressions in `packages/graphrag-llm/tests/integration/`
- [x] T028 [P] Run `uv run poe check` (format + lint + typecheck) to confirm zero errors
- [x] T029 Update `AGENTS.md` with new `huggingface` optional extra and tokenizer technology (already done by agent-context script)
- [x] T030 [P] Add semversioner change entry: `uv run semversioner add-change -t minor -d "Add HuggingFace tokenizer backend for non-OpenAI models."`
- [x] T031 [P] Update `docs/research/packages_todos.md` — mark P3 as completed

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Stories (Phase 3–5)**: All depend on Foundational phase completion
  - US1 → US2 → US3 in priority order
  - US1 and US2 are both P1 but US2 depends on US1's factory registration
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### Within Each User Story

- Tests MUST be written and FAIL before implementation (Red-Green-Refactor)
- Models/config before factory registration
- Factory registration before router updates
- Core implementation before edge case handling

### Parallel Opportunities

- T002, T003, T004 can be done sequentially (config enum → config model → config validation)
- T005, T006 (Foundational tests) are [P] — can run in parallel
- T007–T011 (US1 tests) are [P] — can run in parallel
- T015–T017 (US2 tests) are [P] — can run in parallel
- T020–T022 (US3 tests) are [P] — can run in parallel
- T026–T031 (Polish) are [P] — can run in parallel after all stories

### Story Dependency Chain

```
Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (US1) → Phase 4 (US2) → Phase 5 (US3) → Phase 6 (Polish)
```

US1 MUST complete before US2 (US2's router depends on factory registration from US1).
US3 depends on US1 (consistency tests require HuggingFaceTokenizer to exist).

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all US1 tests together (different files):
Task: "Unit test: HuggingFaceTokenizer.encode() produces valid integer token IDs"
Task: "Unit test: HuggingFaceTokenizer.decode() round-trips correctly"
Task: "Unit test: HuggingFaceTokenizer.num_tokens() returns len(encode(text))"
Task: "Unit test: HuggingFaceTokenizer loads from local tokenizer.json"
Task: "Unit test: create_tokenizer() with huggingface returns HuggingFaceTokenizer"
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run `uv run poe check` + `uv run poe test_unit` — verify HuggingFaceTokenizer works
5. This gives a usable tokenizer — developers can manually configure `type="huggingface"` for non-OpenAI models

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 → Manual `type="huggingface"` config works (tokenizer functional but no auto-routing)
3. US2 → Auto-routing works (system picks right tokenizer based on model name)
4. US3 → Edge cases handled, consistency verified
5. Polish → All tests pass, docs updated, semversioner entry added

### Suggested MVP Scope

Complete Phases 1, 2, and 3. This delivers a working `HuggingFaceTokenizer` that developers can use by setting `tokenizer.type = "huggingface"` and `tokenizer.model_id = "<model_repo>"`. US2 (auto-routing) and US3 (edge cases) are important but the core functionality is complete with US1.

---

## Notes

- Total tasks: **31**
- US1: 9 tasks (5 tests + 4 implementation)
- US2: 5 tasks (3 tests + 2 implementation)
- US3: 6 tasks (3 tests + 3 implementation)
- Polish: 6 tasks
- No test tasks generated for `get_tokenizer()` router in Phase 2 — it's covered by integration tests in US2
- All HuggingFace Hub download tests should use mock/fixture for network calls in unit tests; integration tests can do real downloads
- The `HuggingFaceTokenizer.__init__()` should accept `**kwargs` for extra fields in TokenizerConfig (via `model_dump()` with `extra="allow"`)
