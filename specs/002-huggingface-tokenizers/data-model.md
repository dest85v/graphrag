# Data Model: HuggingFace Tokenizer Integration

## Overview

This feature adds a new tokenizer backend to the GraphRAG LLM package. No persistent data storage is involved — the data model describes in-memory configuration objects and runtime type relationships.

## Entities

### TokenizerConfig

Extends the existing `TokenizerConfig` Pydantic model with validation for the new `huggingface` type.

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `str` (enum) | Yes | Tokenizer backend identifier. Values: `"tiktoken"`, `"huggingface"`. |
| `model_id` | `str \| None` | Conditional | Model identifier. For `huggingface`: HuggingFace model repository path (e.g. `"meta-llama/Llama-3.1-8B-Instruct"`) or local `tokenizer.json` file path. For `tiktoken`: model name for encoding resolution (e.g. `"gpt-4o"`). |
| `encoding_name` | `str \| None` | Conditional | Tiktoken encoding name (e.g. `"cl100k_base"`). Only used when `type = "tiktoken"`. |

**Validation rules**:

- When `type = "huggingface"`: `model_id` MUST be non-empty string.
- When `type = "tiktoken"`: at least one of `model_id` or `encoding_name` MUST be non-empty.
- Empty strings are rejected for all required fields.

### TokenizerType (enum)

Extends the existing `TokenizerType` StrEnum.

**Members**:

| Value | String | Description |
|-------|--------|-------------|
| `Tiktoken` | `"tiktoken"` | OpenAI-compatible tokenizer via tiktoken library. |
| `HuggingFace` | `"huggingface"` | General-purpose tokenizer via HuggingFace tokenizers library. |

### HuggingFace-backed Tokenizer (runtime class)

Implementations of the `Tokenizer` ABC using the HuggingFace `tokenizers` library.

**Runtime attributes**:

| Attribute | Type | Description |
|-----------|------|-------------|
| `_tokenizer` | `tokenizers.Tokenizer` | The underlying HuggingFace tokenizer instance. |
| `_source` | `str` | Source identifier: either the Hub model ID or the local file path. |

**Interface** (inherited from `Tokenizer` ABC):

| Method | Return Type | Description |
|--------|-------------|-------------|
| `encode(text: str)` | `list[int]` | Encode text to token IDs (no special tokens prepended). |
| `decode(tokens: list[int])` | `str` | Decode token IDs back to text. |
| `num_tokens(text: str)` | `int` | Count tokens in text. |
| `num_prompt_tokens(messages)` | `int` | Count tokens in a chat prompt. |

### TokenizerFactory registry

The `TokenizerFactory` registry is extended with a new entry:

| Key | Initializer | Scope |
|-----|-------------|-------|
| `"huggingface"` | `HuggingFaceTokenizer` | `singleton` |

## Relationships

```
TokenizerConfig ──type──> TokenizerType (Tiktoken | HuggingFace)
TokenizerConfig ──model_id──> Hub model ID | local file path
TokenizerFactory ──registry──> Tiktoken (existing) | HuggingFace (new)
HuggingFaceTokenizer ──uses──> tokenizers.Tokenizer (from tokenizers lib)
get_tokenizer() ──routes──> Tiktoken (OpenAI models) | HuggingFace (other models)
```

## State Transitions

No state transitions. The tokenizer type is fixed at configuration time and does not change at runtime.

## Validation Flow

```
TokenizerConfig created
    │
    ├─ type == "huggingface"
    │   ├─ model_id is None ──> ValidationError: "model_id required for huggingface"
    │   ├─ model_id is empty ──> ValidationError: "model_id required for huggingface"
    │   └─ valid model_id ──> OK
    │
    └─ type == "tiktoken"
        ├─ both model_id and encoding_name empty ──> ValidationError
        ├─ model_id valid ──> OK (resolve encoding at runtime)
        └─ encoding_name valid ──> OK
```
