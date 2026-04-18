# Data Model: Russian Language Support

## Overview

This document defines the data models and configuration structures changed or introduced by the Russian language support feature.

## Changed Models

### TextAnalyzerConfig

**File**: `packages/graphrag/graphrag/config/models/extract_graph_nlp_config.py`

**Change**: Add optional `nlp_model` field.

```python
class TextAnalyzerConfig(BaseModel):
    # Existing fields...
    model_name: str = Field(
        default=graphrag_config_defaults.extract_graph_nlp.text_analyzer.model_name,
        description="The spaCy model to use for noun phrase extraction.",
    )
    
    # NEW FIELD
    nlp_model: str | None = Field(
        default=None,
        description="Override the default NLP model name. If None, uses the default (en_core_web_md). Supports any spaCy model name (e.g., 'ru_core_news_md', 'xx_ent_wiki_sm').",
    )
```

**Relationship**: Used by `ExtractGraphNlpConfig` (parent) → passed to `NounPhraseExtractorFactory.get_np_extractor()`.

### NounPhraseExtractorFactory

**File**: `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/factory.py`

**Change**: No model-level changes. Factory already passes `model_name` to all extractors. The `model_name` field in `TextAnalyzerConfig` is the configuration entry point.

## New Data

### Stop Words

**File**: `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/stop_words.py`

**Addition**: `RU_STOP_WORDS` list.

```python
EN_STOP_WORDS = { ... }  # existing

# NEW
RU_STOP_WORDS: frozenset[str] = frozenset({
    "И", "ИЛИ", "НО", "А", "В", "НА", "К", "КЕ", "ПО",
    "ОТ", "ДО", "С", "У", "К", "ДЛЯ", "ЧТО", "КОТОРЫЙ",
    "ЭТОТ", "ЭТА", "ЭТО", "ЭТИ", "ТАКОЙ", "ТАК",
    # ... expanded list
})
```

**Purpose**: Filter out common Russian function words from noun phrase extraction.

### Noun Phrase Grammar Rules (Russian)

**File**: `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/cfg_extractor.py`

**Addition**: `RU_NOUN_PHRASE_GRAMMARS` dictionary — optional grammar rules for CFGExtractor.

```python
RU_NOUN_PHRASE_GRAMMARS: dict[tuple[str, ...], str] = {
    ("ADJ", "NOUN"): "прилагательное + существительное",
    ("NOUN", "PREP", "NOUN"): "существительное + предлог + существительное",
    ("ADV", "ADJ", "NOUN"): "наречие + прилагательное + существительное",
    ("PROPN", "NOUN"): "имя собственное + существительное",
}
```

**Purpose**: Improve CFGExtractor accuracy for Russian text when user specifies `nlp_model: "ru_core_news_md"`.

## Token Validation Model

**File**: `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/regex_extractor.py`

**Change**: `_is_valid_token()` method signature unchanged, implementation changed.

| Aspect | Before | After |
|--------|--------|-------|
| Regex pattern | `^[a-zA-Z0-9\-]+\n?$` | `^\w+[\-]?\w*$` |
| Unicode support | No — ASCII only | Yes — all Unicode word characters |
| Hyphen support | Yes | Yes (explicit in pattern) |
| New dependency | None | None |

**Validation matrix**:

| Token | Before | After |
|-------|--------|-------|
| "внутренний" | ✗ rejected | ✓ accepted |
| "АУДИТ" | ✗ rejected | ✓ accepted |
| "API" | ✓ accepted | ✓ accepted |
| "endpoint" | ✓ accepted | ✓ accepted |
| "deployment-pipeline" | ✓ accepted | ✓ accepted |
| "настройка API" | ✗ (space) | ✗ (space) — handled by noun_chunks |
| "2026" | ✓ accepted | ✓ accepted |
| "v2.0" | ✗ (dot) | ✗ (dot) — handled by noun_chunks |

## Entity Relationships

```
ExtractGraphNlpConfig
    └── TextAnalyzerConfig (nlp_model → model_name)
            └── NounPhraseExtractorFactory.get_np_extractor()
                    ├── SyntacticNounPhraseExtractor(model_name=...)
                    ├── CFGNounPhraseExtractor(model_name=..., ru_grammars=...)
                    └── RegexENNounPhraseExtractor(model_name=..., unicode_valid=true)
```
