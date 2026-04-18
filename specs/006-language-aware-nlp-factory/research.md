# Research: Language-Aware NLP Factory

**Feature**: `006-language-aware-nlp-factory`
**Date**: 2026-04-18

## Summary

Research section for language-aware NLP factory. All technical unknowns were resolved through codebase analysis — no external research required.

## Technical Decisions

### Decision 1: `language` field type — `str | None`
**Rationale**: Pydantic `str | None` with `default=None` is the standard approach in this codebase. Matches existing patterns (e.g., `nlp_model: str | None`). Ensures backward compatibility — missing field = current behavior.
**Verified**: `TextAnalyzerConfig` already uses this pattern for `nlp_model`.

### Decision 2: Stop words source — `RU_STOP_WORDS` already defined
**Rationale**: `RU_STOP_WORDS` is defined in `stop_words.py:23-34` as `frozenset[str]`. Factory currently imports only `EN_STOP_WORDS`. Change: import both, select based on language.
**Verified**: `RU_STOP_WORDS` contains 34 Russian stop words (И, ИЛИ, НО, В, НА, К, ПО, etc.). Type is `frozenset`, needs conversion to `list` for factory (factory expects `list[str]`).

### Decision 3: CFG grammars — rename + extract
**Rationale**: 
- `RU_NOUN_PHRASE_GRAMMARS` in `cfg_extractor.py:19-31` is dead code. Rename to `CFG_NOUN_PHRASE_GRAMMARS` for clarity.
- English grammars are currently hard-coded in `defaults.py:172-180` as `TextAnalyzerDefaults.noun_phrase_grammars`. Extract to `EN_NOUN_PHRASE_GRAMMARS` in `cfg_extractor.py` for single source of truth.
**Verified**: Grammars use universal POS tags (`PROPN,PROPN`, `NOUN,NOUN`, etc.) which work across languages. `ru_core_news_md` supports these tags.

### Decision 4: Language-to-spaCy-model mapping
**Rationale**: Simple dict with fallback. Extensible for adding languages later.
```python
LANGUAGE_MODEL_MAP = {
    "ru": "ru_core_news_md",
    "de": "de_core_news_md",
    "fr": "fr_core_news_md",
    "xx": "xx_ent_wiki_sm",
}
```
**Fallback**: `"en_core_web_md"` for `None`, `""`, `"en"`, or unknown languages.
**Verified**: All these model names follow spaCy convention. `xx_ent_wiki_sm` is the official multilingual model.

### Decision 5: Factory merge strategy for CFG grammars
**Rationale**: When user provides grammars, merge with base grammars (base first, user overrides). This allows selective overrides without full grammar specification.
```python
grammars = base_grammars.copy()
grammars.update(user_grammars)  # user overrides base
```
**Verified**: Follows standard pydantic config merge pattern used elsewhere.

## No Open Questions

All NEEDS CLARIFICATION resolved during spec phase. No external research or documentation review required.
