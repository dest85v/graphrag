# Contract: Chunking Configuration

## Overview

This document defines the contract for the `chunking` configuration section in GraphRAG's `config.yaml`. The `nltk_language` field is added to support multilingual sentence tokenization.

## Configuration Schema

### YAML Configuration

```yaml
chunking:
  type: tokens                    # [tokens, sentence, ...]
  size: 1200                      # int — target chunk size
  overlap: 100                    # int — chunk overlap
  encoding_model: o200k_base      # string — token encoding model
  nltk_language: english          # [NEW] string — NLTK Punkt language (default: english)
```

### Field: `nltk_language`

| Property | Value |
|---|---|
| Type | `string` |
| Required | No (optional, defaults to `"english"`) |
| Default | `"english"` |
| Valid Values | Any string supported by NLTK PUNKT: `english`, `russian`, `german`, `french`, `spanish`, `portuguese`, `italian`, `dutch`, `norwegian`, `swedish`, `danish`, `finnish`, `greek`, `turkish`, `polish`, `catalan`, `romanian`, `croatian`, `serbian` |
| Behavior | Passed to `nltk.sent_tokenize(text, language=...)` when `type: sentence` |
| Impact | Only affects `chunking.type: sentence`. `type: tokens` is unaffected. |
| Backward Compat | Existing configs without this field continue to work (defaults to `english`) |
| NLTK Model Source | Models are bundled in `punkt_tab` package (downloaded by `bootstrap()`) |

## Programmatic Contract (Python)

### ChunkingConfig (Pydantic model)

```python
class ChunkingConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    
    type: str = Field(default=ChunkerType.Tokens)
    encoding_model: str | None = Field(default=None)
    size: int = Field(default=1200)
    overlap: int = Field(default=100)
    prepend_metadata: list[str] | None = Field(default=None)
    nltk_language: str = Field(default="english")  # [NEW]
```

### SentenceChunker (class interface)

```python
class SentenceChunker(Chunker):
    def __init__(
        self,
        encode: Callable[[str], list[int]] | None = None,
        nltk_language: str = "english",  # [NEW]
        **kwargs: Any,
    ) -> None: ...
    
    def chunk(
        self,
        text: str,
        transform: Callable[[str], str] | None = None,
    ) -> list[TextChunk]:
        # [MODIFIED] uses nltk.sent_tokenize(text, language=self._nltk_language)
        ...
```

### create_chunker (factory function)

```python
def create_chunker(
    config: ChunkingConfig,
    encode: Callable[[str], list[int]] | None = None,
    decode: Callable[[list[int]], str] | None = None,
) -> Chunker:
    # [NO CHANGE] config.model_dump() includes nltk_language
    # [NO CHANGE] passed via init_args=config_model to chunker.__init__()
    ...
```

## Error Contract

| Scenario | Error Type | Error Message |
|---|---|---|
| Invalid language code | `LookupError` (from NLTK) | `Unknown punkt language "<language>"` |
| NLTK not installed | `ImportError` | Already handled by existing NLTK import |
| Missing `punkt_tab` model | `LookupError` (from NLTK) | `Resource punkt_tab not found` |

No custom error wrapping is added. NLTK's native errors propagate to the caller.

## Migration Guide

### For existing users (no config changes needed)

No action required. Existing `config.yaml` files without `nltk_language` will default to `"english"`.

### For users wanting Russian sentence chunking

Add to `config.yaml`:
```yaml
chunking:
  type: sentence
  nltk_language: russian
  size: 1200
  overlap: 100
```

### For users wanting other language sentence chunking

```yaml
chunking:
  type: sentence
  nltk_language: german  # or french, spanish, italian, etc.
```
