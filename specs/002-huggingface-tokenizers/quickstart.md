# Quickstart: HuggingFace Tokenizers

## Overview

This feature adds HuggingFace-backed tokenization to GraphRAG, enabling accurate token counting for any model hosted on HuggingFace Hub — not just OpenAI models.

## Installation

The HuggingFace tokenizer is an optional extra. Install it alongside the base package:

```bash
pip install graphrag-llm[huggingface]
```

This adds:
- `tokenizers>=0.21,<0.23` — HuggingFace Rust tokenizer engine
- `sentencepiece>=0.2,<0.3` — for models using SentencePiece tokenization (T5, BART)
- `protobuf>=5.0,<6.0` — transitive dependency of sentencepiece

## Basic Usage

### Automatic tokenizer selection

The simplest approach — just configure your model and let GraphRAG pick the right tokenizer:

```python
from graphrag_llm.config import ModelConfig
from graphrag_llm.tokenizer import get_tokenizer

# OpenAI model → uses tiktoken (fast, cached)
config = ModelConfig(model_provider="openai", model="gpt-4o")
tokenizer = get_tokenizer(model_config=config)
print(tokenizer.num_tokens("Hello, world!"))  # Uses cl100k_base encoding

# Llama model → uses HuggingFace tokenizer
config = ModelConfig(model_provider="openai", model="meta-llama/Llama-3.1-8B-Instruct")
tokenizer = get_tokenizer(model_config=config)
print(tokenizer.num_tokens("Hello, world!"))  # Downloads tokenizer from Hub (cached after 1st use)
```

### Explicit HuggingFace tokenizer

For full control, configure the tokenizer explicitly:

```python
from graphrag_llm.config import TokenizerConfig
from graphrag_llm.tokenizer import create_tokenizer

# From HuggingFace Hub (downloads on first use, caches locally)
config = TokenizerConfig(type="huggingface", model_id="mistralai/Mistral-7B-Instruct-v0.3")
tokenizer = create_tokenizer(config)

# From a local tokenizer.json file (no network required)
config = TokenizerConfig(type="huggingface", model_id="/path/to/tokenizer.json")
tokenizer = create_tokenizer(config)
```

### Token counting

```python
text = "The quick brown fox jumps over the lazy dog."
token_ids = tokenizer.encode(text)
print(f"Tokens: {token_ids}")
print(f"Count: {len(token_ids)}")

# Round-trip
decoded = tokenizer.decode(token_ids)
print(f"Decoded: {decoded}")
```

### Chat prompt token counting

```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is 2+2?"},
]
count = tokenizer.num_prompt_tokens(messages)
print(f"Prompt tokens: {count}")
```

## Supported Models

The HuggingFace tokenizer supports any model that has a `tokenizer.json` or `tokenizer_config.json` on HuggingFace Hub, including:

| Family | Example model_id | Tokenization type |
|--------|-----------------|-------------------|
| Llama | `meta-llama/Llama-3.1-8B-Instruct` | BPE (byte-level) |
| Mistral | `mistralai/Mistral-7B-Instruct-v0.3` | BPE |
| Qwen | `Qwen/Qwen2.5-7B-Instruct` | BPE (byte-level) |
| Gemma | `google/gemma-2-2b-it` | SentencePiece |
| BERT | `bert-base-uncased` | WordPiece |
| T5 | `t5-small` | SentencePiece |

## Performance

| Scenario | Latency | Notes |
|----------|---------|-------|
| First load from Hub | 500ms – 3s | Depends on model size (1–10MB) and network |
| Subsequent loads (cached) | <50ms | Loaded from `~/.cache/huggingface/hub/` |
| encode() per 1K chars | <1ms | Rust-optimized, single-threaded |
| decode() per 1K tokens | <1ms | Rust-optimized |

## Troubleshooting

### Hub unreachable

If HuggingFace Hub is unreachable and no cached tokenizer exists:

```
ValueError: Cannot download tokenizer for 'meta-llama/Llama-3.1-8B-Instruct'.
  Hub unreachable. Provide a local tokenizer.json path, or configure a fallback tokenizer.
```

**Fixes**:
1. Use a local tokenizer.json: `TokenizerConfig(type="huggingface", model_id="/path/to/tokenizer.json")`
2. Pre-download the tokenizer and cache it in a shared location accessible to all runners.

### Missing sentencepiece

For models that use SentencePiece tokenization (T5, BART, some older models), if `sentencepiece` is not installed:

```
ImportError: sentencepiece is required for this tokenizer. Install with: pip install sentencepiece
```

**Fix**: `pip install sentencepiece`

### Model not found on Hub

```
ValueError: Model 'unknown-model/my-model' not found on HuggingFace Hub.
  Verify the model_id is correct and the model has a tokenizer.json file.
```

**Fix**: Check the model repository on HuggingFace Hub for the presence of `tokenizer.json` or `tokenizer_config.json`.
