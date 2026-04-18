# Quickstart: Language-Aware NLP Factory

**Feature**: `006-language-aware-nlp-factory`
**Date**: 2026-04-18

## Overview

After this feature, GraphRAG automatically selects appropriate NLP resources (stop words, CFG grammars, optional spaCy model) based on the `language` field in `extract_graph_nlp.text_analyzer`.

## Before (current)

```yaml
extract_graph_nlp:
  text_analyzer:
    extractor_type: syntactic_parser
    model_name: ru_core_news_md
    # exclude_nouns: EN_STOP_WORDS = ["stuff", "thing", "things", ...]
    # noun_phrase_grammars: English defaults
```

English stop words are used regardless of document language. Russian text extraction is suboptimal.

## After (with feature)

### Minimal Russian config

Set `language: ru` — stop words and CFG grammars selected automatically:

```yaml
extract_graph_nlp:
  text_analyzer:
    extractor_type: syntactic_parser
    language: ru              # ← selects RU_STOP_WORDS + ru_core_news_md
    model_name: ru_core_news_md
```

### Auto spaCy model (optional, P2)

Skip `model_name` entirely — model selected from language:

```yaml
extract_graph_nlp:
  text_analyzer:
    extractor_type: syntactic_parser
    language: ru              # ← selects ru_core_news_md automatically
    # model_name: not needed
```

### CFG extractor with Russian grammars

```yaml
extract_graph_nlp:
  text_analyzer:
    extractor_type: cfg
    language: ru              # ← selects CFG_NOUN_PHRASE_GRAMMARS
    model_name: ru_core_news_md
```

### Override stop words

Explicit `exclude_nouns` bypasses language-based selection:

```yaml
extract_graph_nlp:
  text_analyzer:
    extractor_type: syntactic_parser
    language: ru
    model_name: ru_core_news_md
    exclude_nouns: ["И", "ЧТО", "CUSTOM"]  # user-defined
```

### Backward compatibility

No `language` field — English behavior, exactly as before:

```yaml
extract_graph_nlp:
  text_analyzer:
    extractor_type: regex_english
    # language: not set → EN_STOP_WORDS (current behavior)
```

## Supported Languages

| `language` value | Stop words | CFG grammars | spaCy model (auto) |
|---|---|---|---|
| `null` / not set | EN_STOP_WORDS | EN_NOUN_PHRASE_GRAMMARS | en_core_web_md |
| `en` | EN_STOP_WORDS | EN_NOUN_PHRASE_GRAMMARS | en_core_web_md |
| `ru` | RU_STOP_WORDS | CFG_NOUN_PHRASE_GRAMMARS | ru_core_news_md |
| any other | EN_STOP_WORDS (fallback) | EN_NOUN_PHRASE_GRAMMARS (fallback) | en_core_web_md (fallback) |

## Testing

### Unit test: stop words selection

```python
# language: ru → RU_STOP_WORDS
config = TextAnalyzerConfig(language="ru", extractor_type=Syntactic)
factory = NounPhraseExtractorFactory.get_np_extractor(config)
assert "И" in factory.exclude_nouns
assert "stuff" not in factory.exclude_nouns

# language: en → EN_STOP_WORDS
config = TextAnalyzerConfig(language="en", extractor_type=Syntactic)
factory = NounPhraseExtractorFactory.get_np_extractor(config)
assert "stuff" in factory.exclude_nouns

# language: None → EN_STOP_WORDS (backward compat)
config = TextAnalyzerConfig(language=None, extractor_type=Syntactic)
factory = NounPhraseExtractorFactory.get_np_extractor(config)
assert "stuff" in factory.exclude_nouns

# exclude_nouns set → bypasses language
config = TextAnalyzerConfig(language="ru", exclude_nouns=["CUSTOM"], extractor_type=Syntactic)
factory = NounPhraseExtractorFactory.get_np_extractor(config)
assert "CUSTOM" in factory.exclude_nouns
assert "И" not in factory.exclude_nouns  # RU_STOP_WORDS not applied
```

### Integration test: Russian extraction

```python
# Full NLP pipeline with Russian text
config = TextAnalyzerConfig(
    language="ru",
    extractor_type=Syntactic,
    model_name="ru_core_news_md",
)
extractor = NounPhraseExtractorFactory.get_np_extractor(config)
result = extractor.extract("Модель машинного обучения работает в облаке")
assert "И" not in result  # stop word filtered
assert any("машинного обучения" in phrase.lower() for phrase in result)
```
