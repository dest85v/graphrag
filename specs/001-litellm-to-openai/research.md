# Research: LiteLLM → OpenAI SDK Migration

## Decision 1: Target openai SDK version

**Decision**: Use `openai~=1.60`

**Rationale**: Version 1.60+ is stable and provides all required features:
- `openai.OpenAI`, `openai.AsyncOpenAI` for completions and embeddings
- `openai.AzureOpenAI`, `openai.AsyncAzureOpenAI` for Azure OpenAI
- `openai.pydantic_function_tool` for function calling (already used in `FunctionToolManager`)
- Complete exception hierarchy: `RateLimitError`, `APIConnectionError`, `APITimeoutError`, `AuthenticationError`, `InvalidRequestError`, `PermissionDeniedError`, `APIError`, `ConflictError`, `UnprocessableEntityError`
- `ChatCompletion`, `ChatCompletionChunk`, `CreateEmbeddingResponse` types (already aliased in `types.py`)
- `response_format` for structured output (stable in 1.x)
- `stream` parameter with async iterator support

**Alternatives considered**:
- `openai~=1.50` — Lacks some structured output improvements and latest exception types
- `openai~=1.70` — Newer but not significantly different for our use case; 1.60 is well-established

## Decision 2: Tokenization approach

**Decision**: Replace `litellm.encode/decode` with `tiktoken` directly

**Rationale**: 
- `tiktoken` is already a transitive dependency via `litellm`
- `litellm.encode(model, text)` internally calls `tiktoken.encoding_for_model(model).encode(text)`
- Direct tiktoken usage produces byte-identical results
- The project already has `tiktoken_tokenizer.py` for OpenAI models — extend this pattern

**Implementation**: 
```python
from tiktoken import encoding_for_model
encoding = encoding_for_model(model_id)
tokens = encoding.encode(text)
text = encoding.decode(tokens)
```

**Alternatives considered**:
- Keeping `litellm.encode/decode` — Defeats migration purpose
- HuggingFace `tokenizers` — Planned as P3, not in scope for this migration

## Decision 3: Model cost registry

**Decision**: Bundle OpenAI + Azure OpenAI model costs directly in `model_cost_registry.py`

**Rationale**:
- `litellm.model_cost` contains ~3000 models with pricing across all providers
- This project only uses OpenAI and Azure OpenAI (~50 models)
- Bundling ~50 relevant costs eliminates the `litellm` dependency entirely for this module
- Cost data can be refreshed by updating the bundled dict

**Implementation**: Replace `from litellm import model_cost` with a bundled dict literal:
```python
_MODEL_COST_MAP: dict[str, ModelCosts] = {
    "gpt-4o": {"input_cost_per_token": 0.0000025, "output_cost_per_token": 0.000010},
    # ... ~50 OpenAI/Azure models
}
```

**Alternatives considered**:
- Keeping `litellm.model_cost` — Defeats migration purpose
- Fetching costs at runtime from OpenAI API — Adds network dependency; not currently supported by OpenAI API
- External cost config file — Overly complex for static data

## Decision 4: Backward compatibility strategy

**Decision**: Deprecation alias — `LLMProviderType.LiteLLM = "litellm"` routes to `OpenAICompletion` with `DeprecationWarning`

**Rationale**:
- All existing `config.yaml` files use `type: litellm`
- Breaking this would affect every GraphRAG user
- A deprecation period (target: 2 minor versions) allows gradual migration
- Users see a warning but their pipelines continue working

**Implementation**:
- Keep `LLMProviderType.LiteLLM = "litellm"` enum value
- Add `LLMProviderType.OpenAI = "openai"` as the new recommended value
- In `completion_factory.py` and `embedding_factory.py`, both values register the `OpenAI*` implementation
- Emit `DeprecationWarning` when `type == LiteLLM`

**Alternatives considered**:
- Removing `LiteLLM` immediately — Breaking change, violates FR-011
- Keeping both `LiteLLM*` and `OpenAI*` indefinitely — Technical debt, defeats migration purpose

## Decision 5: Unsupported parameter handling

**Decision**: Silent filtering with debug logging, matching LiteLLM's `drop_params=True` behavior

**Rationale**:
- `LLMCompletionArgs` TypedDict includes fields from `litellm.completion` signature (e.g., `thinking`, `web_search_options`, `function_call`, `functions`)
- OpenAI SDK rejects unknown params with `InvalidRequestError`
- `litellm.completion(drop_params=True)` silently drops unsupported params
- Must match this behavior to avoid breaking existing callers

**Implementation**: Parameter whitelist filter before calling OpenAI SDK:
```python
_SUPPORTED_COMPLETION_PARAMS = {
    "messages", "model", "frequency_penalty", "logit_bias", "logprobs",
    "max_completion_tokens", "max_tokens", "modalities", "n", "parallel_tool_calls",
    "prediction", "presence_penalty", "reasoning_effort", "response_format", "seed",
    "stop", "stream", "stream_options", "temperature", "tool_choice", "tools",
    "top_logprobs", "top_p", "user", "audio", "deployment_id", "extra_headers",
    "safety_identifier",
}
```

**Alternatives considered**:
- Raising errors — Would break existing configs that pass extra params
- Letting OpenAI SDK error — Different error type, breaks `with_errors_for_testing` tests

## Decision 6: Exception type mapping

**Decision**: Direct `getattr(openai, exception_type)` replacement in `with_errors_for_testing`

**Rationale**:
- Both SDKs use identical exception class names: `RateLimitError`, `APIConnectionError`, `APITimeoutError`, `AuthenticationError`, `InvalidRequestError`
- `with_errors_for_testing` uses `exceptions.__dict__.get(exception_type, ValueError)`
- Replacement: `getattr(openai, exception_type, ValueError)` — one-line change
- No behavior change for any existing test scenario

**Alternatives considered**:
- Creating a custom exception mapping layer — Unnecessary complexity; names are identical
- Wrapping openai exceptions in litellm-like exceptions — Adds indirection, no benefit

## Decision 7: Streaming chunk compatibility

**Decision**: No changes needed — `LLMCompletionChunk` is already a type alias for `openai.ChatCompletionChunk`

**Rationale**:
- `types.py:51`: `LLMCompletionChunk = ChatCompletionChunk` (imported from `openai.types.chat.chat_completion_chunk`)
- `LLMChoiceChunk = ChunkChoice` (also from openai.types)
- OpenAI SDK streaming returns the same `ChatCompletionChunk` type
- The `LLMCompletionResponse` already extends `openai.ChatCompletion`
- Chunk iteration in `lite_llm_completion.py:271-273` already uses `chunk.model_dump()` — same interface

**Alternatives considered**: N/A — no changes required
