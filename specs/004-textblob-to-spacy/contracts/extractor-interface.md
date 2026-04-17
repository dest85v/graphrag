# Contract: NounPhraseExtractor Interface

## Overview

This document defines the contract for noun phrase extractors in GraphRAG. The `RegexENNounPhraseExtractor` must comply with this interface to ensure seamless integration with the `NounPhraseExtractorFactory` and downstream consumers.

## Interface: BaseNounPhraseExtractor

### `extract(text: str) -> list[str]`

**Purpose**: Extract noun phrases from raw text.

**Parameters**:
| Name | Type | Required | Description |
|---|---|---|---|
| `text` | `str` | Yes | Input text to extract noun phrases from |

**Returns**: `list[str]` — List of extracted noun phrases, uppercase, deduplicated.

**Invariants**:
- All returned phrases are uppercased
- All returned phrases are non-empty
- No duplicate phrases
- Empty string input returns empty list
- No exceptions for invalid Unicode or non-English text (graceful degradation)

**Example**:
```python
extractor = NounPhraseExtractorFactory.get_np_extractor(config)
phrases = extractor.extract("The quick brown fox jumps over the lazy dog")
# Expected: ["QUICK BROWN FOX", "LAZY DOG"] or similar (implementation-dependent)
```

### `__init__(model_name: str | None, exclude_nouns: list[str] | None = None, max_word_length: int = 15, word_delimiter: str = " ")`

**Purpose**: Initialize the extractor with configuration.

**Parameters**:
| Name | Type | Required | Default | Description |
|---|---|---|---|---|
| `model_name` | `str \| None` | Yes | — | spaCy model name or `None` for regex-only extractors |
| `exclude_nouns` | `list[str]` | No | `[]` | Stop words to exclude from noun phrases |
| `max_word_length` | `int` | No | `15` | Maximum character length of individual words |
| `word_delimiter` | `str` | No | `" "` | Delimiter character for joining phrase tokens |

**Invariants**:
- `exclude_nouns` stored internally as uppercase
- `max_word_length` must be positive
- Model is loaded on init (or deferred to first `extract()` call)

### `__str__() -> str`

**Purpose**: Return cache key string representation.

**Returns**: `str` — Opaque string used as cache key for `RegexENNounPhraseExtractor`.

**Invariants**:
- Must include all configuration parameters that affect output
- Changes to configuration MUST result in a different string
- String must not contain special characters that break filesystem/dict keys

**RegexENNounPhraseExtractor specific format**:
```
regex_en_{model_name}_{exclude_nouns}_{max_word_length}_{word_delimiter}
```

Example: `regex_en_en_core_web_sm_[stuff,thing,things]_15_ `

## Factory Contract: NounPhraseExtractorFactory

### `get_np_extractor(config: TextAnalyzerConfig) -> BaseNounPhraseExtractor`

**Purpose**: Create the correct extractor instance based on configuration type.

**Parameters**:
| Name | Type | Required | Description |
|---|---|---|---|
| `config` | `TextAnalyzerConfig` | Yes | Configuration containing extractor type and parameters |

**Returns**: A concrete `BaseNounPhraseExtractor` subclass instance.

**Supported types** (`NounPhraseExtractorType`):
| Type | Concrete Class |
|---|---|
| `Syntactic` | `SyntacticNounPhraseExtractor` |
| `CFG` | `CFGNounPhraseExtractor` |
| `RegexEnglish` | `RegexENNounPhraseExtractor` |

**Invariants**:
- Factory must not raise on any known `NounPhraseExtractorType`
- All factory-created extractors must implement the `BaseNounPhraseExtractor` interface
- `exclude_nouns` defaults to `EN_STOP_WORDS` when `None`

## Consumer Contract

Consumers of noun phrase extractors (e.g., `build_noun_graph` operation) must:

1. Accept any `BaseNounPhraseExtractor` instance
2. Not depend on implementation-specific methods
3. Handle empty results gracefully (no noun phrases = empty node/edge list)
4. Use `str(extractor)` for cache key generation
