# Contract: Tokenizer Module Public API

## Overview

This document defines the public API contract for the tokenizer module in `graphrag-llm`. All consumers (other packages in the monorepo) rely on this contract for stable behavior.

## Contract: `Tokenizer` ABC

**Module**: `graphrag_llm.tokenizer.Tokenizer`

### `encode(text: str) -> list[int]`

**Contract**:
- Input: UTF-8 string of any length.
- Output: List of non-negative integer token IDs.
- `encode(text)` must produce token IDs that match the target model's API tokenization.
- Special tokens (BOS, EOS) MUST NOT be prepended/appended (consistent with tiktoken behavior).

### `decode(tokens: list[int]) -> str`

**Contract**:
- Input: List of non-negative integer token IDs produced by `encode()`.
- Output: UTF-8 string.
- `decode(encode(text))` must produce a string approximately equal to `text` (within tokenizer-specific tolerance for whitespace/normalization).

### `num_tokens(text: str) -> int`

**Contract**:
- Returns the number of tokens in `text`, equal to `len(encode(text))`.
- Must handle arbitrary UTF-8 input without errors.

### `num_prompt_tokens(messages) -> int`

**Contract**:
- Accepts either a string or a list of message dicts (as per `LLMCompletionMessagesParam`).
- Returns the total token count including role/name/content overhead (OpenAI-compatible counting format).
- Implementation details (tokens_per_message, tokens_per_name) are internal — the contract guarantees consistency with the LLM provider's token counting.

## Contract: `TokenizerType` Enum

**Module**: `graphrag_llm.config.TokenizerType`

### Enum values

| Value | String | Backend |
|-------|--------|---------|
| `Tiktoken` | `"tiktoken"` | tiktoken (OpenAI models only) |
| `HuggingFace` | `"huggingface"` | HuggingFace tokenizers (any model) |

### Stability guarantee

Once released, existing enum values will not be renamed or have their string values changed. New values may be added.

## Contract: `TokenizerConfig` Model

**Module**: `graphrag_llm.config.TokenizerConfig`

### Fields

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `type` | `str` | Yes | Must be one of: `"tiktoken"`, `"huggingface"`. |
| `model_id` | `str \| None` | Conditional | For `"huggingface"`: non-empty string. For `"tiktoken"`: optional model name for encoding resolution. |
| `encoding_name` | `str \| None` | Conditional | For `"tiktoken"`: non-empty encoding name (e.g. `"cl100k_base"`). Ignored for `"huggingface"`. |

### Validation contract

- Validation errors MUST raise `ValueError` with a descriptive message.
- Empty strings (`""`) are rejected for all required fields.
- Unknown `type` values MUST produce a clear error indicating valid options.

## Contract: `create_tokenizer()` Factory

**Module**: `graphrag_llm.tokenizer.create_tokenizer`

### Signature

```python
def create_tokenizer(tokenizer_config: TokenizerConfig) -> Tokenizer:
    ...
```

### Behavior contract

- Given a valid `TokenizerConfig`, returns a `Tokenizer` instance configured as specified.
- Tokenizer instances are cached per-config (singleton per `model_id` / `encoding_name` combination).
- Invalid config MUST raise `ValueError` before returning.
- The returned `Tokenizer` MUST implement all methods of the `Tokenizer` ABC.

## Contract: `register_tokenizer()`

**Module**: `graphrag_llm.tokenizer.register_tokenizer`

### Signature

```python
def register_tokenizer(
    tokenizer_type: str,
    tokenizer_initializer: Callable[..., Tokenizer],
    scope: ServiceScope = "transient",
) -> None:
    ...
```

### Behavior contract

- Registers a new tokenizer type with the factory.
- The `tokenizer_type` string becomes a valid value for `TokenizerConfig.type`.
- The `tokenizer_initializer` is called with the fields of `TokenizerConfig` as keyword arguments.
- Registration is global and persistent for the lifetime of the Python process.
- Registering a type that already exists is a no-op (no error, no override).

## Contract: `get_tokenizer()` Router (graphrag package)

**Module**: `graphrag.tokenizer.get_tokenizer`

### Signature

```python
def get_tokenizer(
    model_config: "ModelConfig | None" = None,
    encoding_model: str | None = None,
) -> Tokenizer:
    ...
```

### Behavior contract

- When `model_config` is provided and the model name matches a known OpenAI model pattern, returns a tiktoken-based tokenizer.
- When `model_config` is provided and the model name does NOT match an OpenAI pattern, returns a HuggingFace-backed tokenizer with `model_id` set to the model name.
- When `model_config` is `None`, falls back to `encoding_model` (or default `o200k_base`) with tiktoken backend.
- The returned tokenizer MUST be a valid `Tokenizer` instance implementing all ABC methods.
