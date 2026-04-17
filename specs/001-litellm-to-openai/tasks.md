---

description: "Task list for replacing LiteLLM with OpenAI SDK in graphrag-llm"

---

# Tasks: Replace LiteLLM with OpenAI SDK

**Input**: Design documents from `/specs/001-litellm-to-openai/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL — no test tasks generated. Verification relies on existing test suites (`poe test`).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g., [US1], [US2], [US3])
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `packages/graphrag-llm/` at repository root
- All file paths are absolute within the monorepo

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the environment and dependency changes

- [x] T001 Update `packages/graphrag-llm/pyproject.toml` — replace `litellm==1.82.6` with `openai~=1.60`, add `tiktoken~=0.8` as explicit dependency
- [x] T002 [P] Run `uv sync` to install the new `openai` and `tiktoken` dependencies
- [x] T003 [P] Verify `litellm` is no longer resolvable: `grep -rn 'import litellm\|from litellm' packages/graphrag-llm/graphrag_llm/` should fail (expected — files still reference litellm, but this confirms dependency is installed)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create shared infrastructure that MUST be complete before any user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 [P] Create `packages/graphrag-llm/graphrag_llm/utils/openai_params.py` — define `CHAT_COMPLETION_PARAMS` set and `filter_completion_kwargs()` function to replace `litellm`'s `drop_params=True` behavior
- [x] T005 [P] Update `packages/graphrag-llm/graphrag_llm/types/types.py` — replace all `from litellm import (...)` imports with direct `openai` imports (remove `AnthropicThinkingParam`, `ChatCompletionModality`, `ChatCompletionPredictionContentParam`, `OpenAIWebSearchOptions` — import from `openai` or remove if unused)
- [x] T006 [P] Update `packages/graphrag-llm/graphrag_llm/config/types.py` — add `OpenAI = "openai"` to `LLMProviderType` enum, keep `LiteLLM = "litellm"` as deprecated alias, remove `LiteLLM` from `TokenizerType` enum
- [x] T007 [P] Update `packages/graphrag-llm/graphrag_llm/model_cost_registry/model_cost_registry.py` — replace `from litellm import model_cost` with bundled `_MODEL_COST_MAP` dict containing ~50 OpenAI/Azure OpenAI models with cost data

**Checkpoint**: Foundation ready — types, config enums, parameter filtering, and cost data are in place

---

## Phase 3: User Story 1 - Seamless Migration for GraphRAG Indexing Users (Priority: P1) 🎯 MVP

**Goal**: Deliver `OpenAICompletion`, `OpenAIEmbedding`, `OpenAITokenizer`, updated mocks, and factory wiring — all existing configs with `type: litellm` work with deprecation warning

**Independent Test**: Run `uv run poe test_integration` and `uv run poe test_unit` — all existing tests pass without modification

- [x] T008 [P] [US1] Create `packages/graphrag-llm/graphrag_llm/tokenizer/openai_tokenizer.py` — `OpenAITokenizer` class using `tiktoken.encoding_for_model(model_id)` for encode/decode, implements `Tokenizer` ABC
- [x] T009 [P] [US1] Update `packages/graphrag-llm/graphrag_llm/tokenizer/tokenizer_factory.py` — register `OpenAITokenizer` for `TokenizerType.Tiktoken` case, remove `LiteLLM` case
- [x] T010 [P] [US1] Create `packages/graphrag-llm/graphrag_llm/completion/openai_completion.py` — `OpenAICompletion` class implementing `LLMCompletion` ABC, wrapping `openai.OpenAI` / `openai.AsyncOpenAI`, with `_create_base_completions()` using `self._sync_client.chat.completions.create()` / `await self._async_client.chat.completions.create()`, parameter filtering via `openai_params.py`, Azure support via `AzureOpenAI`/`AsyncAzureOpenAI` when `model_provider == "azure"`, mock response support via `mock_response` kwarg
- [x] T011 [P] [US1] Create `packages/graphrag-llm/graphrag_llm/embedding/openai_embedding.py` — `OpenAIEmbedding` class implementing `LLMEmbedding` ABC, wrapping `openai.OpenAI` / `openai.AsyncOpenAI`, with `_create_base_embeddings()` using `self._sync_client.embeddings.create()` / `await self._async_client.embeddings.create()`, Azure support via `AzureOpenAI`/`AsyncAzureOpenAI`
- [x] T012 [P] [US1] Update `packages/graphrag-llm/graphrag_llm/completion/mock_llm_completion.py` — remove `import litellm` and `litellm.suppress_debug_info = True` (these were only used to suppress debug output, irrelevant for mock)
- [x] T013 [P] [US1] Update `packages/graphrag-llm/graphrag_llm/embedding/mock_llm_embedding.py` — remove `import litellm` and `litellm.suppress_debug_info = True`
- [x] T014 [US1] Update `packages/graphrag-llm/graphrag_llm/completion/completion_factory.py` — import and register `OpenAICompletion` for `LLMProviderType.LiteLLM` case (replacing `LiteLLMCompletion` import), add `DeprecationWarning` when `type == "litellm"`, update docstring for `tokenizer` parameter
- [x] T015 [US1] Update `packages/graphrag-llm/graphrag_llm/embedding/embedding_factory.py` — import and register `OpenAIEmbedding` for `LLMProviderType.LiteLLM` case (replacing `LiteLLMEmbedding` import), add `DeprecationWarning` when `type == "litellm"`, update docstring for `tokenizer` parameter
- [x] T016 [US1] Update `packages/graphrag-llm/graphrag_llm/config/model_config.py` — change default `type` from `LLMProviderType.LiteLLM` to `LLMProviderType.OpenAI`, rename `_validate_lite_llm_config` to `_validate_openai_config`, update validation docstring, update `_validate_model` to check `LLMProviderType.OpenAI` and `LLMProviderType.LiteLLM`
- [x] T017 [US1] Update `packages/graphrag-llm/graphrag_llm/completion/__init__.py` — update exports to include `OpenAICompletion`, update any litellm references in docstrings
- [x] T018 [US1] Update `packages/graphrag-llm/graphrag_llm/embedding/__init__.py` — update exports to include `OpenAIEmbedding`
- [x] T019 [US1] Update `packages/graphrag-llm/graphrag_llm/completion/lite_llm_completion.py` — replace `import litellm` with `import openai`, replace `from litellm import ModelResponse` with `from openai.types.chat import ChatCompletion`, replace `litellm.completion()` with `self._sync_client.chat.completions.create()`, replace `litellm.acompletion()` with `await self._async_client.chat.completions.create()`, replace `litellm.suppress_debug_info` and `litellm.enable_json_schema_validation` with SDK-native equivalents (structured output via `response_format` param, debug suppressed by default), replace `ModelResponse.model_dump()` with direct attribute access on `ChatCompletion`
- [x] T020 [US1] Update `packages/graphrag-llm/graphrag_llm/embedding/lite_llm_embedding.py` — replace `import litellm` with `import openai`, replace `litellm.embedding()` with `self._sync_client.embeddings.create()`, replace `litellm.aembedding()` with `await self._async_client.embeddings.create()`, replace `litellm.suppress_debug_info` (only suppresss debug, not needed), replace `response.model_dump()` with direct attribute access on `CreateEmbeddingResponse`
- [x] T021 [US1] Update `packages/graphrag-llm/graphrag_llm/completion/completion.py` — fix docstring references to litellm (line 109, 152: `https://docs.litellm.ai/docs/completion/function_call`)

**Checkpoint**: At this point, `OpenAICompletion`, `OpenAIEmbedding`, and `OpenAITokenizer` are wired through factories, backward-compatible with `type: litellm` deprecation warning, and all `import litellm` references are removed from production source files.

---

## Phase 4: User Story 2 - Test Developers Need Reliable Error Simulation (Priority: P1)

**Goal**: Update `with_errors_for_testing` middleware to use `openai` exceptions instead of `litellm.exceptions`, ensuring all test suites produce the same error behavior

**Independent Test**: Run `poe test_integration` — `with_errors_for_testing` scenarios produce expected `openai` exception types

- [x] T022 [P] [US2] Update `packages/graphrag-llm/graphrag_llm/middleware/with_errors_for_testing.py` — replace `import litellm.exceptions as exceptions` with `import openai`, replace `exceptions.__dict__.get(exception_type, ValueError)` with `getattr(openai, exception_type, ValueError)`, update docstring to reference `openai` exceptions instead of `litellm.exceptions`
- [x] T023 [P] [US2] Update `packages/graphrag-llm/graphrag_llm/completion/lite_llm_completion.py` — remove remaining `import litellm` (if any in the file after T019), verify all `litellm.` references are replaced
- [x] T024 [P] [US2] Update `packages/graphrag-llm/graphrag_llm/embedding/lite_llm_embedding.py` — remove remaining `import litellm` references (if any after T020), verify no `litellm.` calls remain

**Checkpoint**: `with_errors_for_testing` produces `openai` exceptions identically to how it previously produced `litellm` exceptions, all test error simulation paths work correctly.

---

## Phase 5: User Story 3 - Tool Calling and Structured Output Work Identically (Priority: P2)

**Goal**: Verify that tool calling (`tools=[...]`), structured output (`response_format`), and streaming work identically through the OpenAI SDK backend

**Independent Test**: Run GraphRAG indexing with tool calling enabled — LLM responses with `tool_calls` are handled correctly by `FunctionToolManager`, structured output parses into Pydantic models

- [x] T025 [P] [US3] Update `packages/graphrag-llm/graphrag_llm/types/types.py` — remove any remaining `from litellm import (...)` type imports (e.g., `AnthropicThinkingParam`, `ChatCompletionModality`, `ChatCompletionPredictionContentParam`, `OpenAIWebSearchOptions`), replace with `openai` equivalents or remove if not directly used (they live in TypedDict defaults)
- [x] T026 [P] [US3] Update `packages/graphrag-llm/graphrag_llm/types/types.py` — update all docstrings referencing "Same signature as litellm.completion" and "Same signature as litellm.embedding" to reference OpenAI SDK signatures
- [x] T027 [P] [US3] Verify `packages/graphrag-llm/graphrag_llm/utils/function_tool_manager.py` — no changes needed (already imports `from openai import pydantic_function_tool`)
- [x] T028 [P] [US3] Verify `packages/graphrag-llm/graphrag_llm/utils/create_completion_response.py` — no changes needed (no litellm dependency)
- [x] T029 [P] [US3] Verify `packages/graphrag-llm/graphrag_llm/utils/create_embedding_response.py` — no changes needed (no litellm dependency)

**Checkpoint**: Tool calling, structured output, and streaming all function identically through the OpenAI SDK backend.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup, verification, and documentation

- [x] T030 [P] Run `uv run poe check` — format + lint + typecheck must pass
- [x] T031 [P] Run `uv run poe test_unit` — all unit tests pass
- [x] T032 [P] Run `uv run poe test_integration` — all integration tests pass (except Azurite-dependent: `test_create_blob_cache`, `test_find` which require Azurite running)
- [x] T033 [P] Run `uv run poe test` — full test suite passes (unit, integration, smoke, notebook, verbs)
- [x] T034 Verify zero litellm imports: `grep -rn 'import litellm\|from litellm' packages/graphrag-llm/graphrag_llm/` returns no output
- [x] T035 Verify backward compatibility: create a `ModelConfig(type="litellm", ...)` and confirm `DeprecationWarning` is emitted and `OpenAICompletion` is instantiated
- [x] T036 Run `.specify/scripts/bash/update-agent-context.sh opencode` to update AGENTS.md with new technology
- [x] T037 Verify `packages/graphrag-llm/graphrag_llm/middleware/with_middleware_pipeline.py` — no litellm references, middleware pipeline works end-to-end with OpenAI implementations
- [x] T038 Verify `packages/graphrag-llm/graphrag_llm/middleware/with_logging.py`, `with_cache.py`, `with_rate_limiting.py`, `with_retries.py`, `with_metrics.py`, `with_request_count.py` — no litellm references in any middleware file

---

## Additional Fixes (Post-Migration)

- [x] T039 Fix `packages/graphrag-llm/graphrag_llm/retry/exceptions_to_skip.py` — remove litellm-only exceptions (`UnsupportedParamsError`, `ContextWindowExceededError`, `ContentPolicyViolationError`, `ImageFetchError`, `InvalidRequestError`, `PermissionDeniedError`, `ServiceUnavailableError`, `BudgetExceededError`), keep only openai SDK exceptions
- [x] T040 Fix `tests/integration/language_model/test_retries.py` — update exception args to be openai-compatible, replace positional arg tuples with factory functions that construct exceptions properly
- [x] T041 Fix `packages/graphrag/graphrag/tokenizer/get_tokenizer.py` — update `TokenizerType.LiteLLM` to `TokenizerType.Tiktoken`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - Phase 3 (US1) and Phase 4 (US2) can run in parallel (different file sets)
  - Phase 5 (US3) depends on Phase 3 and 4 completion (type updates and verifications)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — creates new implementations, updates mocks, wires factories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) — can run in parallel with US1 (different file sets: middleware vs completion/embedding)
- **User Story 3 (P2)**: Can start after US1 + US2 — type updates and verification of tool calling/streaming

### Within Each User Story

- Types/config before implementations (foundational types must exist)
- Factory wiring after implementations exist
- Deprecation updates after factory wiring
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 2**: T004-T007 all [P] — different files, no cross-dependencies
- **Phase 3**: T008-T013 [P] — tokenizer, completion, embedding, mocks are independent files
  - T014-T018 depend on T008-T013 (factory wiring requires implementations to exist)
- **Phase 4**: T022-T024 [P] — middleware and cleanup files are independent
- **Phase 5**: T025-T029 [P] — all verification tasks, no dependencies
- **Phase 6**: T030-T038 [P] — all verification tasks, no cross-dependencies

---

## Parallel Example: Phase 3 (US1)

```bash
# Launch all independent implementation tasks together:
Task: "Create OpenAITokenizer in openai_tokenizer.py" (T008)
Task: "Create OpenAICompletion in openai_completion.py" (T010)
Task: "Create OpenAIEmbedding in openai_embedding.py" (T011)
Task: "Update mock_llm_completion.py" (T012)
Task: "Update mock_llm_embedding.py" (T013)

# After implementations exist, launch factory wiring:
Task: "Update completion_factory.py" (T014)
Task: "Update embedding_factory.py" (T015)
Task: "Update model_config.py" (T016)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run `poe test_integration` — if all tests pass, MVP is complete
5. Users can now run GraphRAG with `openai` SDK behind the scenes

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → MVP delivered (core migration)
3. Add User Story 2 → Test independently → Error simulation works
4. Add User Story 3 → Test independently → Tool calling verified
5. Polish → Full test suite passes, zero litellm imports

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (implementation, mocks, factories)
   - Developer B: User Story 2 (error simulation, middleware)
3. After US1 + US2 complete:
   - Developer A or B: User Story 3 (type cleanup, verification)
4. All: Polish & verification (Phase 6)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- No test tasks generated (verification via existing test suites per SC-001)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- If any task fails verification, fix it before moving to the next task
- `tiktoken` already provides `encoding_for_model()` which maps model names (gpt-4o, text-embedding-ada-002, etc.) to the correct encoding — no manual mapping needed
