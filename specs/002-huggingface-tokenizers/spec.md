# Feature Specification: Add HuggingFace Tokenizers for Non-OpenAI Models

**Feature Branch**: `002-huggingface-tokenizers`  
**Created**: 2026-04-17  
**Status**: Draft  
**Input**: User description: "Надо реализовать задачу 'P3 — Добавить HuggingFace `tokenizers` для не-OpenAI моделей'"

## User Scenarios & Testing

### User Story 1 — Tokenize text for any LLM model (Priority: P1)

A developer configures GraphRAG to use a non-OpenAI model (e.g., Llama, Mistral, Qwen, Gemma) and needs accurate token counting for prompt length management, rate limiting, and chunk size calculations.

**Why this priority**: Without this, any non-OpenAI model produces incorrect token counts or crashes. This is the core capability that the LiteLLM removal broke for these models.

**Independent Test**: Configure a completion model with the tokenizer type set to HuggingFace and the model ID pointing to a HuggingFace model repository. Call the tokenizer factory and verify the token count matches what the HuggingFace `transformers` library reports for the same text.

**Acceptance Scenarios**:

1. **Given** a model config with a Llama model name and tokenizer type set to HuggingFace, **When** the tokenizer factory is invoked, **Then** a HuggingFace-backed tokenizer is returned that correctly encodes and decodes text using that model's tokenizer from the HuggingFace Hub.
2. **Given** a model config with a Qwen model name, **When** the tokenizer factory is invoked, **Then** the tokenizer correctly uses that Qwen model's tokenizer from the HuggingFace Hub.
3. **Given** a local `tokenizer.json` file path, **When** the tokenizer is instantiated with that path, **Then** it loads the tokenizer from the local file without network access.

---

### User Story 2 — Automatic tokenizer selection based on model family (Priority: P1)

A developer uses GraphRAG with an OpenAI model and expects optimal performance (fast, cached tiktoken encoding) without any configuration changes. When using a non-OpenAI model, the system automatically selects the correct HuggingFace tokenizer.

**Why this priority**: Developers should not need to manually configure tokenizers. The system should "just work" for both OpenAI and non-OpenAI models.

**Independent Test**: Configure a completion model with an OpenAI model name — verify the tokenizer factory returns a tiktoken-based tokenizer. Configure a non-OpenAI model name — verify it returns a HuggingFace-backed tokenizer.

**Acceptance Scenarios**:

1. **Given** an OpenAI GPT-4 model name, **When** the tokenizer factory is invoked, **Then** the returned tokenizer uses tiktoken with the `cl100k_base` encoding.
2. **Given** an OpenAI text-embedding model name, **When** the tokenizer factory is invoked, **Then** the returned tokenizer uses tiktoken with the `cl100k_base` encoding.
3. **Given** a Llama model name, **When** the tokenizer factory is invoked, **Then** the returned tokenizer is a HuggingFace-backed tokenizer configured with that model's repository ID.
4. **Given** an unknown model name that matches no known patterns, **When** the tokenizer factory is invoked, **Then** the system falls back to tiktoken with `cl100k_base` encoding (safe default).

---

### User Story 3 — Consistent token counting across all tokenizer backends (Priority: P2)

A developer uses GraphRAG operations (chunking, prompt construction, rate limiting) and needs token counts to be consistent and accurate regardless of which tokenizer backend is in use. Token counts must match what the actual LLM API would count.

**Why this priority**: Inaccurate token counts cause API errors (exceeding max tokens) or wasted API calls (over-estimating). This is critical for production reliability.

**Independent Test**: Compare the HuggingFace-backed tokenizer's `num_tokens()` result against `transformers.AutoTokenizer` for 100 diverse texts across Llama, Mistral, Qwen, and Gemma model families. Verify match rate ≥ 99%.

**Acceptance Scenarios**:

1. **Given** any UTF-8 text string, **When** any tokenizer's `num_tokens()` is called, **Then** the count equals the number of tokens the target model's API would count.
2. **Given** a text with special characters, emojis, and non-ASCII Unicode, **When** any tokenizer's `encode()` is called, **Then** the result is a valid list of integer token IDs.
3. **Given** a list of integer token IDs, **When** `decode()` is called on any tokenizer, **Then** the result round-trips correctly (decode(encode(text)) ≈ text, within tokenizer-specific tolerance).

---

### Edge Cases

- **Unreachable HuggingFace Hub**: When the HuggingFace Hub is unreachable and no cached tokenizer exists, the system logs a clear error and falls back to the `cl100k_base` encoding rather than crashing.
- **Model name ambiguity**: When a model name could match both tiktoken and HuggingFace patterns, tiktoken takes priority (explicit OpenAI model list takes precedence).
- **SentencePiece models**: For models that use SentencePiece tokenization (e.g., T5), the system requires the `sentencepiece` package and provides a clear error if missing.
- **Tokenizer cache invalidation**: When a tokenizer on HuggingFace Hub is updated, the system uses the cached version by default (HuggingFace caching behavior).

## Requirements

### Functional Requirements

- **FR-001**: System MUST provide a HuggingFace-backed tokenizer class that implements the standard tokenizer interface (`encode()`, `decode()`, `num_tokens()`, `num_prompt_tokens()`).
- **FR-002**: System MUST add a `huggingface` tokenizer type to the tokenizer type enum.
- **FR-003**: System MUST register the HuggingFace-backed tokenizer in the tokenizer factory so it can be instantiated via the standard factory method.
- **FR-004**: System MUST update the tokenizer configuration to accept a model ID field for HuggingFace model identifiers (e.g., a HuggingFace model repository path).
- **FR-005**: System MUST validate that the model ID is non-empty when the tokenizer type is set to HuggingFace.
- **FR-006**: System MUST update the tokenizer getter function to route OpenAI models to the tiktoken backend and all other models to the HuggingFace backend.
- **FR-007**: System MUST support loading tokenizers from local tokenizer definition files in addition to downloading from HuggingFace Hub.
- **FR-008**: System MUST add the HuggingFace `tokenizers` library as an optional dependency (extra: `huggingface`), along with `sentencepiece` and `protobuf` for SentencePiece-based models.
- **FR-009**: System MUST ensure consistent token counting behavior between the HuggingFace backend and the tiktoken backend (special tokens not prepended/appended).
- **FR-010**: System MUST maintain backward compatibility — existing configs using the tiktoken tokenizer type continue to work without changes.

### Key Entities

- **HuggingFace-backed tokenizer**: Tokenizer implementation using the HuggingFace `tokenizers` library. Accepts a model ID (HuggingFace model repository identifier or local tokenizer definition file path).
- **Tokenizer type enum**: Extended enum with a new `huggingface` value for selecting the HuggingFace tokenizer backend.
- **Tokenizer configuration**: Extended config with a `model_id` field that works for both `tiktoken` and `huggingface` types.
- **Tokenizer getter**: Router function that selects tokenizer backend based on model name (OpenAI family → tiktoken, others → HuggingFace).

## Success Criteria

### Measurable Outcomes

- **SC-001**: HuggingFace-backed tokenizer token counts match the HuggingFace `transformers.AutoTokenizer` counts for ≥ 99% of test strings across Llama, Mistral, Qwen, and Gemma model families.
- **SC-002**: The tokenizer getter correctly routes ≥ 95% of common non-OpenAI model names (from a curated list of 50 popular models) to the HuggingFace backend.
- **SC-003**: HuggingFace tokenizer loads from cached Hub download in under 2 seconds on subsequent calls (first download excluded).
- **SC-004**: All existing unit and integration tests for the existing tiktoken-based tokenizers continue to pass without modification.
- **SC-005**: Zero regressions in token counting for OpenAI models — token counts must remain identical to the pre-feature baseline.

## Assumptions

- The HuggingFace `tokenizers` library is stable and production-ready — it is the same engine used by the `transformers` library and is widely adopted in the ML community.
- HuggingFace Hub will be accessible during initial tokenizer download (caches locally for offline use afterward).
- GraphRAG users may configure models from any HuggingFace model repository, not just specific pre-approved models.
- The `model_id` field in the tokenizer configuration will accept HuggingFace model repository identifiers or local file paths to tokenizer definition files.
- Tiktoken will remain the default for OpenAI models — no changes to existing OpenAI tokenizer behavior.
- The `sentencepiece` and `protobuf` dependencies are optional extras, needed only for models that use SentencePiece tokenization (e.g., T5, BART).
