# Quickstart: Verify LiteLLM → OpenAI SDK Migration

## Prerequisites

- Python 3.11–3.13
- `uv` installed for dependency management
- Access to OpenAI API key or Azure OpenAI endpoint (for integration verification)

## Step 1: Install Dependencies

```bash
uv sync
```

After migration, verify `openai~=1.60` and `tiktoken~=0.8` are in `packages/graphrag-llm/pyproject.toml` and `litellm` is removed.

## Step 2: Run Unit Tests

```bash
uv run poe test_unit
```

All unit tests must pass without modification. Key test targets:
- `tests/unit/config/test_model_config.py` — Config validation for OpenAI and Azure
- `tests/unit/config/test_tokenizer_config.py` — Tokenizer type validation
- `tests/unit/chunking/test_chunker.py` — Tokenizer integration

## Step 3: Run Integration Tests

```bash
uv run poe test_integration
```

Key integration targets:
- `tests/integration/language_model/test_factory.py` — Factory creates `OpenAICompletion` / `OpenAIEmbedding`
- `tests/integration/language_model/test_retries.py` — Retry middleware with openai exceptions
- `tests/integration/language_model/test_rate_limiter.py` — Rate limiting with tiktoken tokenizer

## Step 4: Backward Compatibility Check

Create a test config with `type: litellm` and verify:

```python
from graphrag_llm.config import ModelConfig, LLMProviderType
from graphrag_llm.completion import create_completion

config = ModelConfig(
    type="litellm",  # deprecated value
    model_provider="openai",
    model="gpt-4o",
    api_key="sk-test",
)

# Should emit DeprecationWarning and return OpenAICompletion instance
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    completion = create_completion(config)
    assert any("litellm" in str(warning.message).lower() for warning in w)
```

## Step 5: Tokenization Parity

```python
from graphrag_llm.tokenizer import OpenAITokenizer

tokenizer = OpenAITokenizer(model_id="gpt-4o")
text = "Hello, world! This is a test of tokenization parity."

tokens = tokenizer.encode(text)
decoded = tokenizer.decode(tokens)

assert decoded == text  # Byte-identical round-trip
assert isinstance(tokens, list)
assert all(isinstance(t, int) for t in tokens)
```

Compare output with `tiktoken` directly:

```python
import tiktoken
encoding = tiktoken.encoding_for_model("gpt-4o")
assert tokenizer.encode(text) == encoding.encode(text)
```

## Step 6: Full Test Suite

```bash
uv run poe test
```

All test suites (unit, integration, smoke, notebook, verbs) must pass.

## Step 7: Code Quality Gate

```bash
uv run poe check
```

Format + lint + typecheck must pass.

## Step 8: Verify Zero litellm Imports

```bash
grep -rn 'import litellm\|from litellm' packages/graphrag-llm/graphrag_llm/
```

Expected: no output (zero matches in production source files).

## Troubleshooting

### ImportError: No module named 'litellm'

If tests fail with `ImportError` for `litellm`, check that:
1. `litellm` has been removed from `pyproject.toml` dependencies
2. No test files still import `litellm` directly (tests should use `mock` or the new implementations)

### AttributeError: module 'openai' has no attribute 'RateLimitError'

Ensure `openai~=1.60` or later. Earlier 1.x versions may have different exception module structure.

### Tokenization mismatch between OpenAITokenizer and existing tests

Verify that `model_id` passed to `OpenAITokenizer` matches the model expected by tests. The tokenizer resolves the encoding via `tiktoken.encoding_for_model(model_id)` — if the model name doesn't match a known tiktoken encoding, it falls back to `cl100k_base`.
