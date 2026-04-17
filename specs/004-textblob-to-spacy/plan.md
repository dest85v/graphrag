# Implementation Plan: Переход RegexENNounPhraseExtractor с textblob на spaCy

**Branch**: `004-textblob-to-spacy` | **Date**: 2026-04-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-textblob-to-spacy/spec.md`

## Summary

Заменить внутренний бэкенд `RegexENNounPhraseExtractor` с textblob на spaCy, убрав зависимость `textblob` и связанные NLTK-корпуса. Новая реализация использует `doc.noun_chunks` как источник noun phrases, `token.pos_ == "PROPN"` для proper nouns, и переиспользует существующие хелперы из `np_validator.py`. Конфигурация и API остаются полностью обратосовместимыми.

## Technical Context

**Language/Version**: Python 3.11–3.13 (per `requires-python = ">=3.11,<3.14"`)  
**Primary Dependencies**: `spacy~=3.8` (already in `packages/graphrag/pyproject.toml:54`), `nltk~=3.9` (already in pyproject.toml, will be reduced)  
**Storage**: N/A  
**Testing**: pytest with `asyncio_mode = "auto"`, suites: `unit`, `integration`  
**Target Platform**: Linux server (graph indexing pipeline)  
**Project Type**: Library (monorepo, `packages/graphrag` package)  
**Performance Goals**: Извлечение noun phrases не медленнее textblob более чем на 20% на наборе из 1000+ документов  
**Constraints**: Обратная совместимость API (сигнатуры `__init__`, `extract`, `__str__`), семантика фильтрации 1:1, использование существующих `np_validator.py` хелперов  
**Scale/Scope**: Один класс (`RegexENNounPhraseExtractor`) в `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/`, ~124 строки кода, ~30 строк тестов (предполагаются)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Constitution Principle | Compliance | Notes |
|---|---|---|
| **I. Library-First Architecture** | PASS | Изменение внутри одного пакета (`graphrag`), без новых зависимостей между пакетами. Публичный API класса не меняется. |
| **II. CLI Interface** | PASS | CLI `graphrag index` использует экстрактор через `NounPhraseExtractorFactory` — сигнатуры не меняются. |
| **III. Test-First (NON-NEGOTIABLE)** | PASS | Реализация будет preceded unit-тестами. Red-Green-Refactor cycle будет соблюден. |
| **IV. Integration Testing** | PASS | Новые интеграционные тесты: сравнение output старого vs нового экстрактора на наборе текстов. |
| **V. Versioning & Change Management** | PASS | semversioner change entry будет добавлен перед merge (patch: cleanup/refactor). |

**Result**: All gates pass. No complexity justified needed.

## Project Structure

### Documentation (this feature)

```text
specs/004-textblob-to-spacy/
├── plan.md              # This file
├── research.md          # Phase 0 output — resolved
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (extractor contract)
└── tasks.md             # Phase 2 output (not created by /speckit.plan)
```

### Source Code (repository root)

```text
packages/graphrag/
├── graphrag/index/operations/build_noun_graph/np_extractors/
│   ├── regex_extractor.py          # ← MODIFIED: textblob → spaCy
│   ├── np_validator.py             # ← REUSED: is_compound(), has_valid_token_length()
│   ├── base.py                     # ← REUSED: load_spacy_model()
│   ├── factory.py                  # ← NO CHANGE (factory pattern unchanged)
│   ├── cfg_extractor.py            # ← NO CHANGE
│   ├── syntactic_parsing_extractor.py  # ← NO CHANGE
│   └── stop_words.py               # ← NO CHANGE
├── pyproject.toml                  # ← MODIFIED: remove textblob dependency
├── tests/unit/
│   └── test_regex_noun_extractor.py  # ← NEW: unit tests for spaCy-based extractor
└── tests/integration/
    └── test_noun_phrase_consistency.py  # ← NEW: cross-backend comparison tests
```

**Structure Decision**: Изменение локализовано внутри одного пакета `graphrag` и одного подкаталога `np_extractors`. Новые тесты добавлены в существующие директории `tests/unit/` и `tests/integration/`.

## Complexity Tracking

Not applicable — no constitution violations, no architectural complexity beyond established patterns.

## Phase 0: Research Summary

All technical unknowns resolved (see `research.md`):

1. **spaCy API**: `doc.noun_chunks` → noun phrases, `token.pos_ == "PROPN"` → proper nouns, `doc.ents` → named entities (optional for this extractor).
2. **Model**: `en_core_web_sm` — smallest English model, download-capable via `spacy.cli.download`.
3. **POS mapping**: spaCy Universal POS tags (PROPN, NOUN) map to textblob Penn Treebank behavior for noun phrase filtering.
4. **Filtering logic**: Reuse `np_validator.py` helpers (`is_compound`, `has_valid_token_length`) + regex for token validation.
5. **Cache key**: `__str__()` updated to include model name — cache invalidation is acceptable side-effect.

## Phase 1: Design & Implementation Plan

### Step 1: Update `regex_extractor.py`

**File**: `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/regex_extractor.py`

Changes:
1. Remove `from textblob import TextBlob` import
2. Remove all `nltk` corpus downloads (`brown`, `treebank`, `punkt`, `punkt_tab`, `averaged_perceptron_tagger_eng`)
3. Replace `__init__`: use `load_spacy_model("en_core_web_sm", exclude=["lemmatizer", "parser", "ner"])` — note: we exclude parser and NER since we only need POS tagging and noun chunks
4. Replace `extract()`:
   - `doc = self.nlp(text)`
   - `proper_nouns = [token.text.upper() for token in doc if token.pos_ == "PROPN"]`
   - `noun_phrase_texts = [chunk.text for chunk in doc.noun_chunks]`
   - For each noun phrase, apply the same `_tag_noun_phrases()` filtering logic
5. Update `__str__()` to: `f"regex_en_{self.model_name}_{self.exclude_nouns}_{self.max_word_length}_{self.word_delimiter}"`

### Step 2: Remove `textblob` dependency

**File**: `packages/graphrag/pyproject.toml`

Remove line 56: `"textblob~=0.18",`

### Step 3: Write unit tests

**File**: `tests/unit/test_regex_noun_extractor.py` (NEW)

Tests:
- `test_extract_returns_uppercase_phrases`: output is uppercased
- `test_extract_filters_exclude_nouns`: excluded stop words are not in output
- `test_extract_handles_empty_text`: empty string → empty list
- `test_extract_handles_unicode`: Unicode text processed without errors
- `test_extract_max_word_length`: words > max_word_length are filtered
- `test_extract_compound_words`: hyphenated compound words are preserved
- `test_extract_proper_nouns`: proper nouns are detected
- `test_str_cache_key`: `__str__()` includes model name
- `test_extract_invalid_tokens`: non-alphanumeric tokens are filtered

### Step 4: Write integration tests

**File**: `tests/integration/test_noun_phrase_consistency.py` (NEW)

Tests:
- `test_regex_spacy_vs_cfg_consistency`: spaCy-based regex extractor output compared against CFG extractor on same inputs (Jaccard similarity >= 0.85)
- `test_regex_spacy_vs_real_text`: Extractor produces valid noun phrases on real-world documents

### Step 5: Verify and run checks

- `uv run poe format` — format code
- `uv run poe check` — lint + typecheck
- `uv run poe test_unit` — run unit tests
- `uv run poe test_integration` — run integration tests

## Phase 2: Testing & Validation

1. Run full test suite: `uv run poe test`
2. Run `uv run poe check` for format/lint/typecheck
3. Manual verification: run `graphrag index` on sample data with `RegexEnglish` extractor
4. Add semversioner change entry: `uv run semversioner add-change -t patch -d "Replace textblob with spaCy in RegexENNounPhraseExtractor."`
