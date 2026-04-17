# Contracts: graphrag-llm Public API

## Overview

This document captures the public API contracts of `graphrag-llm` that MUST remain stable through the LiteLLM → OpenAI SDK migration. These are the interfaces that external packages (`graphrag`, `graphrag-chunking`, etc.) depend on.

## Factory Contracts

### `create_completion(model_config, *, cache, cache_key_creator, tokenizer) → LLMCompletion`

**File**: `packages/graphrag-llm/graphrag_llm/completion/__init__.py`

**Contract**:
- Accepts `ModelConfig` with `type` field (`"openai"`, `"litellm"`, or `"mock"`)
- Returns an instance implementing `LLMCompletion` ABC
- `tokenizer` parameter is optional — if None, creates one from `ModelConfig.model_id`
- All other parameters (cache, rate limiter, retrier, metrics) are configured via `ModelConfig`

**Signature must not change**.

### `create_embedding(model_config, *, cache, cache_key_creator, tokenizer) → LLMEmbedding`

**File**: `packages/graphrag-llm/graphrag_llm/embedding/__init__.py`

**Contract**:
- Accepts `ModelConfig` with `type` field (`"openai"`, `"litellm"`, or `"mock"`)
- Returns an instance implementing `LLMEmbedding` ABC
- `tokenizer` parameter is optional

**Signature must not change**.

### `create_tokenizer(config) → Tokenizer`

**File**: `packages/graphrag-llm/graphrag_llm/tokenizer/__init__.py`

**Contract**:
- Accepts `TokenizerConfig` with `model_id` field
- Returns an instance implementing `Tokenizer` ABC
- Default tokenizer is `Tiktoken` (using `cl100k_base` encoding)

**Signature must not change**.

## ABC Contracts

### `LLMCompletion` (ABC)

**File**: `packages/graphrag-llm/graphrag_llm/completion/completion.py`

**Abstract methods** (signatures must not change):
- `completion(**kwargs) → LLMCompletionResponse | Iterator[LLMCompletionChunk]`
- `completion_async(**kwargs) → LLMCompletionResponse | AsyncIterator[LLMCompletionChunk]`
- `metrics_store → MetricsStore` (property)
- `tokenizer → Tokenizer` (property)

**Concrete methods** (behavior must not change):
- `completion_thread_pool(response_handler, concurrency, queue_limit)` — context manager
- `completion_batch(completion_requests, concurrency, queue_limit)` — batch processing

### `LLMEmbedding` (ABC)

**File**: `packages/graphrag-llm/graphrag_llm/embedding/embedding.py`

**Abstract methods** (signatures must not change):
- `embedding(**kwargs) → LLMEmbeddingResponse`
- `embedding_async(**kwargs) → LLMEmbeddingResponse`
- `metrics_store → MetricsStore` (property)
- `tokenizer → Tokenizer` (property)

**Concrete methods** (behavior must not change):
- `embedding_thread_pool(response_handler, concurrency, queue_limit)` — context manager
- `embedding_batch(embedding_requests, concurrency, queue_limit)` — batch processing

## Response Type Contracts

### `LLMCompletionResponse`

**File**: `packages/graphrag-llm/graphrag_llm/types/types.py`

**Contract**:
- Extends `openai.ChatCompletion`
- Adds `formatted_response: ResponseFormat | None` property
- Adds `content: str` computed property (returns `choices[0].message.content or ""`)
- `model_dump()` returns dict compatible with `LLMCompletionResponse(**dict)` reconstruction

### `LLMEmbeddingResponse`

**File**: `packages/graphrag-llm/graphrag_llm/types/types.py`

**Contract**:
- Extends `openai.CreateEmbeddingResponse`
- Adds `embeddings: list[list[float]]` computed property
- Adds `first_embedding: list[float]` computed property

### `LLMCompletionChunk`

**File**: `packages/graphrag-llm/graphrag_llm/types/types.py`

**Contract**: Type alias for `openai.ChatCompletionChunk`. Must support:
- `model_dump()` → dict
- `choices[0].delta.content` (str | None)
- `choices[0].delta.tool_calls` (list | None)

## Config Contracts

### `ModelConfig` (Pydantic BaseModel)

**File**: `packages/graphrag-llm/graphrag_llm/config/model_config.py`

**Fields** (must not be removed or have their types changed):
- `type: str` — LLM provider type (default: `LLMProviderType.LiteLLM` → will change to `OpenAI`)
- `model_provider: str` — Provider name (e.g., `"openai"`, `"azure"`)
- `model: str` — Model name (e.g., `"gpt-4o"`)
- `api_base: str | None` — Base URL
- `api_version: str | None` — API version
- `api_key: str | None` — API key
- `auth_method: AuthMethod` — Auth type
- `azure_deployment_name: str | None` — Azure deployment name
- `call_args: dict[str, Any]` — Extra kwargs
- `retry: RetryConfig | None`
- `rate_limit: RateLimitConfig | None`
- `metrics: MetricsConfig | None`
- `mock_responses: list[str] | list[float]`

### `TokenizerConfig` (Pydantic BaseModel)

**File**: `packages/graphrag-llm/graphrag_llm/config/tokenizer_config.py`

**Fields**:
- `model_id: str` — Model identifier

## Middleware Contract

### `with_errors_for_testing(*, sync_middleware, async_middleware, failure_rate, exception_type, exception_args)`

**File**: `packages/graphrag-llm/graphrag_llm/middleware/with_errors_for_testing.py`

**Contract**:
- Returns `tuple[LLMFunction, AsyncLLMFunction]`
- `exception_type` parameter uses string names from exception module (`"RateLimitError"`, etc.)
- Exception type resolution uses `getattr(module, exception_type, ValueError)`
- Must support all exception types previously supported via `litellm.exceptions`

## Deprecation Contract

When `LLMProviderType.LiteLLM = "litellm"` is used in `ModelConfig.type`:
- A `DeprecationWarning` MUST be emitted
- The `OpenAICompletion` / `OpenAIEmbedding` implementation is used
- All behavior is identical to the deprecated `LiteLLM*` classes
