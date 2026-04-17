# Research: HuggingFace Tokenizers Integration

## Decision 1: Use `tokenizers` library (PyO3/Rust bindings)

**Decision**: Use the HuggingFace `tokenizers` library (v0.21+) for all non-OpenAI tokenization.

**Rationale**:
- `tokenizers` is the same Rust-based engine used by `transformers.AutoTokenizer`, guaranteeing identical tokenization
- PyO3 bindings provide native performance (no Python interpreter overhead in the hot path)
- Single dependency — no need for the full `transformers` library (which is ~800MB with all extras)
- Supports all common model families: BPE (Llama, Mistral, Qwen, Gemma), WordPiece (BERT), SentencePiece (T5)
- Python >=3.9 required (project uses 3.11+)
- Apache 2.0 license
- No hard dependencies — `sentencepiece` is optional, needed only for models that use SPM tokenization

**Alternatives considered**:
- `transformers.AutoTokenizer`: Full-featured but heavyweight (~800MB). Overkill when we only need tokenization.
- `sentencepiece` directly: Only covers SPM models, not BPE/WordPiece. Would require multiple libraries.
- Manual tokenizer JSON parsing: Fragile, unmaintained, no longer supported by HuggingFace.

## Decision 2: Library version — `tokenizers>=0.21,<0.23`

**Decision**: Pin to `tokenizers>=0.21,<0.23`.

**Rationale**:
- 0.21.x (released Nov 2024 – Jun 2025) is the most widely adopted stable line
- 0.22.x (released Aug 2025 – Jan 2026) is the latest but newer; 0.21.x has broader pre-built wheels
- Both 0.21 and 0.22 share the same stable API surface (`Tokenizer.from_pretrained`, `encode`, `decode`, `from_file`)
- Upper bound prevents breaking changes from 0.23+

## Decision 3: API surface — `Tokenizer` class with `add_special_tokens=False`

**Decision**: Use `Tokenizer.from_pretrained(model_id)` and `tokenizer.encode(text, add_special_tokens=False).ids` for encoding.

**Rationale**:
- `add_special_tokens=False` is critical for consistency with tiktoken (tiktoken does not add BOS/EOS tokens)
- `.ids` attribute on `Encoding` returns `list[int]` — directly compatible with our `Tokenizer.encode()` return type
- `tokenizer.decode(ids, skip_special_tokens=True)` for decoding
- `Tokenizer.from_file(path)` for loading local `tokenizer.json`

**API confirmed via DeepWiki documentation of `huggingface/tokenizers` v6.1.1 Python bindings**:
```python
from tokenizers import Tokenizer

# From HuggingFace Hub
tokenizer = Tokenizer.from_pretrained("meta-llama/Llama-3.1-8B-Instruct")

# From local file
tokenizer = Tokenizer.from_file("/path/to/tokenizer.json")

# Encode (add_special_tokens=False for tiktoken compatibility)
encoded = tokenizer.encode("Hello world", add_special_tokens=False)
token_ids: list[int] = encoded.ids  # [128000, 32361, 9064]

# Decode
text = tokenizer.decode(token_ids, skip_special_tokens=True)  # "Hello world"

# Token count
num_tokens = len(encoded.ids)
```

## Decision 4: Optional dependencies — `sentencepiece` and `protobuf` as extras

**Decision**: Add `sentencepiece` and `protobuf` as part of the `huggingface` extra (not bare dependencies).

**Rationale**:
- `sentencepiece` is only needed for models using SPM tokenization (T5, BART, some older models)
- `protobuf` is a transitive dependency of `sentencepiece` (pinned to avoid conflicts)
- BPE and WordPiece models (Llama, Mistral, Qwen, BERT, GPT-2) do NOT require sentencepiece
- Keeping these optional minimizes install size for the common case

**Dependencies**:
```toml
[project.optional-dependencies]
huggingface = [
    "tokenizers>=0.21,<0.23",
    "sentencepiece>=0.2,<0.3",   # Optional: only for SPM models
    "protobuf>=5.0,<6.0",        # Transitive dep of sentencepiece
]
```

## Decision 5: Model detection heuristic for auto-routing

**Decision**: Maintain an explicit list of known OpenAI model name patterns for tiktoken routing. Everything else routes to HuggingFace.

**Rationale**:
- Explicit list is simpler, faster, and more predictable than regex/guessing
- OpenAI model naming is consistent and well-documented
- Unknown models safely fall back to HuggingFace (which handles unknown models with a clear error from the Hub)
- If a user has a custom model that tiktoken supports, they can explicitly set `tokenizer.type = "tiktoken"` in config

**Known OpenAI model patterns** (for tiktoken routing):
```
gpt-4o, gpt-4o-mini, gpt-4, gpt-4-turbo, gpt-3.5-turbo
text-embedding-ada-002, text-embedding-3-small, text-embedding-3-large
cl100k_base
```

## Decision 6: HuggingFace Hub caching behavior

**Decision**: Rely on `tokenizers` default caching — first download from Hub, subsequent loads from local cache.

**Rationale**:
- `Tokenizer.from_pretrained()` uses `huggingface_hub` internally, which caches to `~/.cache/huggingface/hub/`
- First load downloads model files (typically 1-10MB for tokenizer.json)
- Subsequent loads are instant (from disk cache)
- No additional caching layer needed

## Decision 7: Error handling for Hub-unreachable scenarios

**Decision**: Catch network errors during `from_pretrained()` and fall back to a configurable fallback tokenizer (default: tiktoken `cl100k_base`).

**Rationale**:
- HuggingFace Hub may be unreachable in air-gapped environments
- A clear error message + graceful fallback prevents hard crashes
- Users can pre-download tokenizers or use local `tokenizer.json` files
