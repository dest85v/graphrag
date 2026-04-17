# Data Model: LiteLLM → OpenAI SDK Migration

## Overview

This migration does not introduce new entities or modify existing data models. All types (`LLMCompletionResponse`, `LLMCompletionChunk`, `LLMEmbeddingResponse`, `LLMCompletionArgs`, `LLMEmbeddingArgs`) are already defined in terms of `openai` types and remain compatible. The only change is the internal implementation of the completion, embedding, and tokenizer classes.

## Type Compatibility Matrix

| Type | Current Source | New Source | Compatible |
|---|---|---|---|
| `LLMCompletionResponse` | `openai.ChatCompletion` (via `litellm.ModelResponse.model_dump()`) | `openai.ChatCompletion` (via `OpenAI.chat.completions.create()`) | ✅ Identical |
| `LLMCompletionChunk` | `openai.ChatCompletionChunk` (type alias) | `openai.ChatCompletionChunk` (from streaming) | ✅ Identical |
| `LLMEmbeddingResponse` | `openai.CreateEmbeddingResponse` (via `litellm.embedding().model_dump()`) | `openai.CreateEmbeddingResponse` (via `OpenAI.embeddings.create()`) | ✅ Identical |
| `LLMChoice` | `openai.Choice` (type alias) | `openai.Choice` | ✅ Identical |
| `LLMCompletionMessage` | `openai.ChatCompletionMessage` (type alias) | `openai.ChatCompletionMessage` | ✅ Identical |
| `LLMCompletionUsage` | `openai.CompletionUsage` (type alias) | `openai.CompletionUsage` | ✅ Identical |
| `LLMEmbedding` | `openai.Embedding` (type alias) | `openai.Embedding` | ✅ Identical |
| `LLMEmbeddingUsage` | `openai.Usage` (type alias) | `openai.Usage` | ✅ Identical |
| `LLMCompletionFunctionToolParam` | `openai.ChatCompletionFunctionToolParam` (type alias) | `openai.ChatCompletionFunctionToolParam` | ✅ Identical |

## Configuration Model — Changes

### ModelConfig (`config/model_config.py`)

**Before**:
```python
type: str = Field(default=LLMProviderType.LiteLLM, ...)
def _validate_lite_llm_config(self) -> None: ...
```

**After**:
```python
type: str = Field(default=LLMProviderType.OpenAI, ...)
def _validate_openai_config(self) -> None: ...
```

- Default value changes from `LLMProviderType.LiteLLM` to `LLMProviderType.OpenAI`
- Validation method renamed to `_validate_openai_config()`
- Validation logic is identical: checks `api_base` for Azure, validates auth method

### LLMProviderType (`config/types.py`)

**Before**:
```python
class LLMProviderType(StrEnum):
    LiteLLM = "litellm"
    MockLLM = "mock"
```

**After**:
```python
class LLMProviderType(StrEnum):
    OpenAI = "openai"
    LiteLLM = "litellm"  # Deprecated: routes to OpenAI
    MockLLM = "mock"
```

- `OpenAI` added as the new primary value
- `LiteLLM` retained as deprecated alias (routes to OpenAI with warning)

### TokenizerType (`config/types.py`)

**Before**:
```python
class TokenizerType(StrEnum):
    LiteLLM = "litellm"
    Tiktoken = "tiktoken"
```

**After**:
```python
class TokenizerType(StrEnum):
    Tiktoken = "tiktoken"
```

- `LiteLLM` removed — `Tiktoken` is the only tokenizer type for OpenAI models
- `OpenAITokenizer` uses `tiktoken` directly (same as `TiktokenTokenizer` but with different initialization)

## Tokenizer Models

| Tokenizer Class | Encoding | Supported Models |
|---|---|---|
| `OpenAITokenizer` (new) | `tiktoken.encoding_for_model(model_id)` | Any OpenAI model (gpt-4o, gpt-3.5-turbo, text-embedding-*) |
| `TiktokenTokenizer` (existing) | Fixed encoding by `encoding_name` | cl100k_base, p50k_base, r50k_base, pkl50k_edit |

**Difference**: `OpenAITokenizer` resolves the encoding from the model ID at runtime (via tiktoken's internal mapping). `TiktokenTokenizer` uses a user-specified encoding name. Both produce identical results for OpenAI models.

## Model Cost Registry

**Before**: `litellm.model_cost` — dict of ~3000 models across all providers

**After**: Bundled `_MODEL_COST_MAP` — dict of ~50 OpenAI + Azure OpenAI models

**Coverage**: All models currently referenced in GraphRAG configs:
- `gpt-4o`, `gpt-4o-mini` (completions)
- `gpt-4`, `gpt-3.5-turbo` (legacy, for backward compatibility)
- `text-embedding-ada-002`, `text-embedding-3-small`, `text-embedding-3-large` (embeddings)
- Azure deployments reference the same model costs
