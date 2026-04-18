# Contract: TextAnalyzerConfig nlp_model field

## Overview

This contract documents the `nlp_model` configuration field added to `TextAnalyzerConfig`, which allows users to select a spaCy model for noun phrase extraction.

## Interface

**Configuration field**: `TextAnalyzerConfig.nlp_model`

**Type**: `str | None`

**Default**: `None` (falls back to `defaults.extract_graph_nlp.text_analyzer.model_name`)

## Schema

```yaml
# graphrag.yaml example
models:
  graph_extraction:
    strategy:
      type: graphrag_nlp
      config:
        # NEW: Optional override for the spaCy model name
        nlp_model: "ru_core_news_md"  # or "xx_ent_wiki_sm", "en_core_web_md"
        
        # Existing fields (unchanged):
        # extractor_type: syntactic | cfg | regex_english
        # max_word_length: 15
        # exclude_nouns: [...]
        # word_delimiter: " "
```

## Valid Values

| Value | Description | Package Required |
|-------|-------------|-----------------|
| `"en_core_web_md"` | English model (default) | pre-installed with spaCy |
| `"ru_core_news_md"` | Russian monolingual model | `uv add graphrag[nlp-ru]` |
| `"xx_ent_wiki_sm"` | Universal multilingual NER | `uv add graphrag[nlp-xx]` |
| Any other spaCy model name | Custom model | Model must be installed |

## Behavior

1. If `nlp_model` is `None`, the default model name from `defaults.py` is used (`en_core_web_md`).
2. If `nlp_model` is a string, it is passed to `spacy.load()`.
3. If the model is not found, `BaseNounPhraseExtractor.load_spacy_model()` attempts `spacy.cli.download()` automatically.
4. If download also fails, a clear `OSError` is raised with the model name.

## Validation

| Input | Result |
|-------|--------|
| `null` / omitted | Uses default (`en_core_web_md`) |
| `"en_core_web_md"` | Loads English model |
| `"ru_core_news_md"` | Loads Russian model |
| `"xx_ent_wiki_sm"` | Loads multilingual model |
| `"nonexistent-model"` | Attempts download → raises `OSError` if unavailable |
| `""` (empty string) | Raises `OSError` from `spacy.load("")` |

## Backward Compatibility

- **No breaking change**: Default behavior (`nlp_model=None` → `en_core_web_md`) is identical to current behavior.
- **No API change**: `TextAnalyzerConfig` constructor accepts `nlp_model` as optional keyword arg with `default=None`.
- **No config migration**: Existing `graphrag.yaml` files work unchanged.
