# Implementation Plan: Add HuggingFace Tokenizers for Non-OpenAI Models

**Branch**: `002-huggingface-tokenizers` | **Date**: 2026-04-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-huggingface-tokenizers/spec.md`

## Summary

Add a HuggingFace-backed tokenizer to the `graphrag-llm` package, enabling accurate token counting for any LLM model hosted on HuggingFace Hub (Llama, Mistral, Qwen, Gemma, etc.). This fills the gap left by the P2 migration (LiteLLM → OpenAI SDK), which removed LiteLLM's automatic tokenizer routing. The implementation adds a new `TokenizerType.HuggingFace` enum value, a `HuggingFaceTokenizer` class using the `tokenizers` library, and updates the `get_tokenizer()` router to automatically select the correct backend based on model name.

## Technical Context

**Language/Version**: Python 3.11–3.13 (per project `requires-python = ">=3.11,<3.14"`)  
**Primary Dependencies**: `tokenizers>=0.21,<0.23` (HuggingFace Rust tokenizer, PyO3 bindings), `sentencepiece>=0.2,<0.3` (optional, for SPM models), `protobuf>=5.0,<6.0` (optional, transitive of sentencepiece)  
**Storage**: N/A — tokenizer loaded at runtime from HuggingFace Hub cache or local files  
**Testing**: pytest with `asyncio_mode = "auto"`, 1000s default timeout; unit tests in `tests/unit`, integration tests in `tests/integration`  
**Target Platform**: Linux server, any OS with pre-built `tokenizers` wheels (pip supports manylinux, macosx, win_amd64 for Python 3.11–3.13)  
**Project Type**: Library (monorepo package: `graphrag-llm`, used by `graphrag` and other workspace packages)  
**Performance Goals**: Tokenizer load from cached Hub < 50ms; encode/decode < 1ms per 1K tokens/chars  
**Constraints**: `add_special_tokens=False` for consistency with tiktoken; no hard dependency on `sentencepiece` or `protobuf` — these are optional extras; backward compatibility with existing `TokenizerConfig` and `Tokenizer` ABC  
**Scale/Scope**: Affects all GraphRAG operations that count tokens: chunking, prompt construction, rate limiting, workflow orchestration. Single new package (`graphrag-llm`); one new module (`huggingface_tokenizer.py`); modifications to 4 existing modules.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Library-First Architecture
**PASS.** The feature adds one new class (`HuggingFaceTokenizer`) in the `graphrag-llm` package. It extends existing abstractions (`Tokenizer` ABC, `TokenizerFactory`, `TokenizerConfig`) without creating new packages. All changes are contained within the LLM package.

### II. CLI Interface
**N/A.** This feature does not add CLI functionality. Tokenizer selection is configured via `ModelConfig`/`TokenizerConfig` in YAML/Python configs and invoked programmatically.

### III. Test-First (NON-NEGUCABLE)
**PASS.** Implementation will follow Red-Green-Refactor. Tests will be written before code:
- Unit tests for `HuggingFaceTokenizer.encode()`/`decode()`/`num_tokens()`
- Unit tests for `TokenizerType.HuggingFace` enum value
- Unit tests for `TokenizerConfig` validation (huggingface type + model_id)
- Unit tests for `create_tokenizer()` factory with HuggingFace backend
- Integration tests for `get_tokenizer()` routing (OpenAI → tiktoken, other → HuggingFace)
- Cross-backend consistency test: `HuggingFaceTokenizer.num_tokens()` vs `transformers.AutoTokenizer`

### IV. Integration Testing
**PASS.** New integration tests will validate:
- Cross-package: `graphrag.get_tokenizer()` → `graphrag_llm.create_tokenizer()` → `HuggingFaceTokenizer`
- Factory routing for both OpenAI and non-OpenAI models
- Token counting consistency across backends

### V. Versioning & Change Management
**PASS.** A semversioner change entry will be added before merge. The change is MINOR (new tokenizer type, non-breaking addition to existing API).

**Post-Design Re-check (after Phase 1)**: All gates still pass. No design changes introduced complexity or violated any principle.

## Project Structure

### Documentation (this feature)

```text
specs/002-huggingface-tokenizers/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output — 7 research decisions
├── data-model.md        # Phase 1 output — TokenizerConfig, TokenizerType, HuggingFaceTokenizer
├── quickstart.md        # Phase 1 output — installation, usage, troubleshooting
├── contracts/
│   └── tokenizer-api.md # Phase 1 output — public API contracts
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
packages/graphrag-llm/graphrag_llm/
├── tokenizer/
│   ├── huggingface_tokenizer.py    # NEW — HuggingFaceTokenizer class
│   ├── tokenizer.py                 # MODIFIED — update docstrings (no API change)
│   ├── tokenizer_factory.py         # MODIFIED — register HuggingFace tokenizer
│   └── openai_tokenizer.py          # UNCHANGED — existing OpenAI/tiktoken tokenizer
├── config/
│   ├── types.py                     # MODIFIED — add TokenizerType.HuggingFace
│   └── tokenizer_config.py          # MODIFIED — add model_id field + validation
├── pyproject.toml                   # MODIFIED — add huggingface extra
```

```text
tests/
├── unit/
│   ├── test_huggingface_tokenizer.py       # NEW — encode/decode/num_tokens tests
│   ├── test_tokenizer_config_validation.py # MODIFIED — add huggingface validation tests
│   └── test_tokenizer_factory.py           # MODIFIED — add HuggingFace registration tests
└── integration/
    └── test_tokenizer_routing.py            # NEW — get_tokenizer() routing tests
```

### Dependency Changes

**`packages/graphrag-llm/pyproject.toml`** — add optional extra:

```toml
[project.optional-dependencies]
huggingface = [
    "tokenizers>=0.21,<0.23",
    "sentencepiece>=0.2,<0.3",
    "protobuf>=5.0,<6.0",
]
```

**`packages/graphrag/pyproject.toml`** — (optional) add `huggingface` extra to the main package if the `graphrag` package itself should offer it.

### Source Code Structure Decision

The feature is a **single-library extension** within the `graphrag-llm` monorepo package. All changes are confined to:
- One new module (`huggingface_tokenizer.py`) in the tokenizer package
- Four existing modules modified for enum, config, factory, and pyproject updates
- One new test file in unit tests, one in integration tests

No new packages, no new top-level modules, no cross-package boundary changes beyond the existing `Tokenizer` ABC and `TokenizerFactory` registry.

## Complexity Tracking

> No constitution violations — all gates passed without justification needed.
