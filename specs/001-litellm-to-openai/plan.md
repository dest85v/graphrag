# Implementation Plan: Replace LiteLLM with OpenAI SDK

**Branch**: `001-litellm-to-openai` | **Date**: 2026-04-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-litellm-to-openai/spec.md`

## Summary

Replace the `litellm` dependency (v1.82.6, ~2000 lines of abstraction code) with the native `openai` SDK (v1.60+) in the `graphrag-llm` package. The migration preserves the exact same public API (`LLMCompletion`, `LLMEmbedding`, `LLMTokenizer` interfaces), backward-compatible config (`type: litellm` still works with deprecation warning), and all middleware plumbing (caching, retries, rate limiting, metrics, logging, error simulation). Intentionally drops multi-provider support (Anthropic, Groq, Bedrock, Vertex AI) — a conscious trade-off to reduce complexity, improve type safety, and simplify debugging.

## Technical Context

**Language/Version**: Python 3.11–3.13 (per project `requires-python = ">=3.11,<3.14"`)  
**Primary Dependencies**: `openai~=1.60` (replaces `litellm==1.82.6`), `tiktoken~=0.8` (already transitive, make direct), `azure-identity~=1.25` (unchanged)  
**Storage**: N/A — pure library package  
**Testing**: `pytest` with `asyncio_mode = "auto"`, 1000s timeout; suites: unit, integration, smoke, notebook, verbs  
**Target Platform**: Linux server (GraphRAG indexing/querying pipelines)  
**Project Type**: Python library (monorepo package: `graphrag-llm`)  
**Performance Goals**: Azure OpenAI completion latency within 5% of `litellm` baseline  
**Constraints**: Must maintain 100% backward compatibility with existing `config.yaml` — `type: litellm` must work with deprecation warning; all existing test suites must pass unchanged  
**Scale/Scope**: ~8 files directly import `litellm`; ~26 call sites to `litellm.*` functions; 5 middleware components; 3 factory registrations; tests in `tests/integration/language_model/` and `tests/unit/config/`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Library-First Architecture — ✅ COMPLIANT
This change is entirely within the `graphrag-llm` package. The package remains self-contained with well-defined interfaces (`LLMCompletion`, `LLMEmbedding`, `LLMTokenizer` ABCs). No new inter-package boundaries are introduced.

### II. CLI Interface — ✅ COMPLIANT
This is an internal library change. The `graphrag` CLI layer is unaffected — it communicates with `graphrag-llm` through the same factory functions (`create_completion`, `create_embedding`), which maintain their existing signatures.

### III. Test-First (NON-NEGOTIABLE) — ✅ COMPLIANT
All new code MUST follow Red-Green-Refactor. The migration plan includes a parallel-run phase where both `LiteLLM*` and `OpenAI*` implementations run on CI to verify parity. All existing tests in `tests/integration/language_model/` and `tests/unit/config/` MUST pass without modification.

### IV. Integration Testing — ✅ COMPLIANT
Cross-package workflows (GraphRAG → graphrag-llm) are validated by existing integration tests. New integration tests will compare `OpenAICompletion` vs `LiteLLMCompletion` output on the same dataset. Azurite-based smoke tests are unaffected (they test storage, not LLM providers).

### V. Versioning & Change Management — ✅ COMPLIANT
This is a MINOR version bump (new implementation path added, existing path deprecated). A `semversioner add-change` entry will be included in the PR.

### Complexity Tracking

No complexity violations. The migration follows a documented 6-step phased approach with parallel-run validation.

## Project Structure

### Documentation (this feature)

```text
specs/001-litellm-to-openai/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
packages/graphrag-llm/
├── pyproject.toml                       # DEPS: remove litellm, add openai, tiktoken
└── graphrag_llm/
    ├── types/types.py                   # CHANGED: replace litellm type imports with openai equivalents
    ├── config/
    │   ├── types.py                     # CHANGED: LLMProviderType.LiteLLM → deprecated alias
    │   └── model_config.py              # CHANGED: rename _validate_lite_llm_config → _validate_openai_config
    ├── completion/
    │   ├── completion_factory.py        # CHANGED: register OpenAICompletion for LiteLLM type
    │   ├── openai_completion.py         # NEW: OpenAICompletion implementation
    │   └── mock_llm_completion.py       # CHANGED: remove litellm imports
    ├── embedding/
    │   ├── embedding_factory.py         # CHANGED: register OpenAIEmbedding for LiteLLM type
    │   ├── openai_embedding.py          # NEW: OpenAIEmbedding implementation
    │   └── mock_llm_embedding.py        # CHANGED: remove litellm imports
    ├── tokenizer/
    │   ├── openai_tokenizer.py          # NEW: OpenAITokenizer using tiktoken directly
    │   └── tokenizer_factory.py         # CHANGED: register OpenAITokenizer
    ├── middleware/
    │   └── with_errors_for_testing.py   # CHANGED: use openai exceptions instead of litellm.exceptions
    ├── model_cost_registry/
    │   └── model_cost_registry.py       # CHANGED: replace litellm.model_cost with bundled data
    └── utils/
        ├── function_tool_manager.py     # UNCHANGED (already uses openai.pydantic_function_tool)
        └── create_completion_response.py # UNCHANGED (no litellm dependency)
```

**Structure Decision**: Single monorepo package. All changes confined to `packages/graphrag-llm/`. No new packages or directories. Existing file paths preserved for deprecated `LiteLLM*` classes (renamed to `openai_*`).

## Phase 0: Research & Clarifications

### Resolved Technical Decisions

**Decision 1: openai SDK version** — Use `openai~=1.60`. This version provides:
- Full Azure OpenAI support (`AzureOpenAI`, `AsyncAzureOpenAI`)
- `pydantic_function_tool` for function calling (already in use by `FunctionToolManager`)
- `ChatCompletion`, `ChatCompletionChunk`, `CreateEmbeddingResponse` types (already aliased in `types.py`)
- Exception hierarchy: `RateLimitError`, `APIConnectionError`, `APITimeoutError`, `AuthenticationError`, `InvalidRequestError`
- Structured output via `response_format` parameter (beta → stable in 1.x)

**Rationale**: `openai` SDK 1.60+ is stable, well-tested, and provides all features needed. The project already imports types from `openai.types.*` in `types.py`, confirming compatibility.

**Alternatives considered**:
- `openai~=1.50` — Missing some recent structured output improvements
- Staying on older `0.x` — Not viable; SDK 0.x API is fundamentally different

**Decision 2: Tokenization — tiktoken directly** — Replace `litellm.encode/decode` with `tiktoken.encoding_for_model(model_id).encode(text)`. Both use the same underlying tiktoken encodings (cl100k_base, p50k_base, etc.).

**Rationale**: `tiktoken` is already a transitive dependency via `litellm`. Direct usage produces identical tokenization. The `tiktoken_tokenizer.py` already exists and works for OpenAI models.

**Alternatives considered**:
- Keeping `litellm.encode/decode` — Defeats the purpose of migration
- HuggingFace `tokenizers` — Out of scope for P2; planned as P3

**Decision 3: Model cost registry — bundle data** — `litellm.model_cost` is a comprehensive dict of ~3000 models with pricing. Replace with a bundled subset of OpenAI + Azure OpenAI model costs (the only providers this project supports).

**Rationale**: The project only uses OpenAI and Azure OpenAI. Bundling ~50 relevant model costs is sufficient and eliminates the `litellm` dependency. Cost data can be refreshed periodically.

**Alternatives considered**:
- Keeping `litellm.model_cost` — Defeats migration purpose
- Fetching costs at runtime from OpenAI API — Adds network dependency and complexity

**Decision 4: Backward compatibility — deprecation alias** — `LLMProviderType.LiteLLM = "litellm"` remains as a value but routes to `OpenAICompletion`. A `DeprecationWarning` is emitted when `type: litellm` is used.

**Rationale**: Existing `config.yaml` files use `type: litellm`. Breaking this would affect every GraphRAG user. A deprecation period allows migration without disruption.

**Alternatives considered**:
- Removing `LiteLLM` enum value immediately — Breaking change, violates FR-011
- Keeping both implementations indefinitely — Technical debt, defeats migration purpose

**Decision 5: Unsupported parameters — silent filter** — Parameters like `thinking`, `web_search_options`, `function_call`, `functions` that exist in `LLMCompletionArgs` but not in OpenAI SDK are silently filtered (replacing `drop_params: True` behavior from LiteLLM). A debug log is emitted for each dropped parameter.

**Rationale**: `litellm.completion(drop_params=True)` silently drops unsupported params. The replacement must match this behavior to avoid test failures. Logging provides visibility without breaking.

**Alternatives considered**:
- Raising errors for unsupported params — Would break existing configs that pass extra params
- Passing all params and letting OpenAI SDK error — Different error type, breaks error handling tests

**Decision 6: Exception mapping — direct replacement** — Map `litellm.exceptions` to `openai` exceptions 1:1. The `with_errors_for_testing` middleware uses `exceptions.__dict__.get(exception_type, ValueError)`. Replace with `getattr(openai, exception_type, ValueError)`.

**Rationale**: Both SDKs have `RateLimitError`, `APIConnectionError`, `AuthenticationError`, `InvalidRequestError`. The exception type names are identical, so a direct `getattr` replacement works.

**Decision 7: Streaming — chunk type compatibility** — `LLMCompletionChunk` already extends `openai.types.chat.chat_completion_chunk.ChatCompletionChunk`. No change needed — the OpenAI SDK returns the same type.

**Rationale**: `types.py:29-30` already imports from `openai.types.chat.chat_completion_chunk`. The `LLMCompletionChunk` is a type alias, not a custom class.

## Phase 1: Design & Contracts

### Data Model

The migration does not introduce new entities. Existing types remain compatible:

| Existing Type | Source | Compatibility |
|---|---|---|
| `LLMCompletionResponse` | Extends `openai.ChatCompletion` | ✅ Already uses openai types |
| `LLMCompletionChunk` | Type alias for `ChatCompletionChunk` | ✅ Already uses openai types |
| `LLMEmbeddingResponse` | Extends `openai.CreateEmbeddingResponse` | ✅ Already uses openai types |
| `LLMCompletionArgs` | TypedDict (litellm.completion signature) | ⚠️ Docstrings reference litellm, body unchanged |
| `LLMEmbeddingArgs` | TypedDict (litellm.embedding signature) | ⚠️ Docstrings reference litellm, body unchanged |

### Migration Steps

The migration follows a 6-phase approach to minimize risk:

**Phase 1 — Create OpenAI implementations (parallel with Phase 2)**
- Create `openai_completion.py` — `OpenAICompletion` class
- Create `openai_embedding.py` — `OpenAIEmbedding` class
- Create `openai_tokenizer.py` — `OpenAITokenizer` class
- Create `utils/openai_params.py` — Parameter filter + supported params whitelist

**Phase 2 — Replace tokenizer (low risk, independent)**
- Replace `LiteLLMTokenizer` with `OpenAITokenizer` in `tokenizer_factory.py`
- Update `TokenizerConfig` — remove `LiteLLM` from `TokenizerType`
- Verify byte-identical tokenization via comparison tests

**Phase 3 — Update mock implementations (low risk, independent)**
- Remove `import litellm` from `mock_llm_completion.py` (only used `litellm.suppress_debug_info`)
- Remove `import litellm` from `mock_llm_embedding.py` (only used `litellm.suppress_debug_info`)

**Phase 4 — Wire factories (medium risk)**
- Update `completion_factory.py` — register `OpenAICompletion` for `LLMProviderType.LiteLLM`
- Update `embedding_factory.py` — register `OpenAIEmbedding` for `LLMProviderType.LiteLLM`
- Update `types.py` — replace `litellm` type imports with direct `openai` imports
- Update `model_cost_registry.py` — replace `litellm.model_cost` with bundled cost data

**Phase 5 — Remove deprecated classes (medium risk)**
- Deprecate `LiteLLMCompletion` — emit warning, route to `OpenAICompletion`
- Deprecate `LiteLLMEmbedding` — emit warning, route to `OpenAIEmbedding`
- Deprecate `LiteLLMTokenizer` — emit warning, route to `OpenAITokenizer`

**Phase 6 — Clean up dependencies (final)**
- Remove `litellm==1.82.6` from `pyproject.toml`
- Add `openai~=1.60`, make `tiktoken` explicit
- Remove remaining `litellm` references in docstrings

### Contract: with_errors_for_testing Migration

The `with_errors_for_testing` middleware must produce identical exception behavior:

**Before (litellm):**
```python
import litellm.exceptions as exceptions
exception_cls = exceptions.__dict__.get(exception_type, ValueError)
raise exception_cls(message)
```

**After (openai):**
```python
import openai
exception_cls = getattr(openai, exception_type, ValueError)
raise exception_cls(message)
```

**Supported exception types** (identical in both SDKs):
- `RateLimitError`
- `APIConnectionError`
- `APITimeoutError`
- `AuthenticationError`
- `InvalidRequestError`
- `PermissionDeniedError`
- `APIError`
- `ConflictError`
- `UnprocessableEntityError`

### Quickstart: Verifying the Migration

To verify the migration is complete and correct:

1. **Run the full test suite**:
   ```bash
   uv run poe test
   ```
   All tests must pass. The suite includes:
   - `tests/unit/` — unit tests for config, chunking, indexing verbs
   - `tests/integration/language_model/` — factory, retries, rate limiter tests
   - `tests/smoke/` — smoke tests (Azurite-dependent)
   - `tests/notebook/` — notebook execution tests
   - `tests/verbs/` — verb-level integration tests

2. **Verify zero litellm imports**:
   ```bash
   grep -rn 'import litellm\|from litellm' packages/graphrag-llm/graphrag_llm/
   ```
   Result: no output (zero matches).

3. **Verify backward compatibility**:
   Create a test config with `type: litellm` and confirm:
   - `create_completion()` returns `OpenAICompletion` instance
   - A `DeprecationWarning` is logged
   - All completion/embedding calls succeed

4. **Verify tokenization parity**:
   Run comparison tests: `OpenAITokenizer.encode(text) == LiteLLMTokenizer.encode(text)` for models: `gpt-4o`, `gpt-4o-mini`, `text-embedding-ada-002`, `text-embedding-3-small`.

5. **Run `poe check`**:
   ```bash
   uv run poe check
   ```
   Format + lint + typecheck must pass.

## Re-evaluation: Constitution Check Post-Design

### I. Library-First — ✅ Still compliant
All changes within `graphrag-llm`. Package boundary unchanged.

### III. Test-First — ✅ Still compliant
6-phase approach with parallel-run CI validation ensures Red-Green-Refactor is followed.

### V. Versioning — ✅ Still compliant
This is a MINOR bump: new implementation path added (`OpenAICompletion`), existing path (`LiteLLM*`) deprecated but functional.
