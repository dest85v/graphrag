# Implementation Plan: Language-Aware NLP Factory

**Branch**: `006-language-aware-nlp-factory` | **Date**: 2026-04-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-language-aware-nlp-factory/spec.md`

## Summary

Добавить поле `language` в `TextAnalyzerConfig` и реализовать в `NounPhraseExtractorFactory` автоподбор стоп-слов и CFG-грамматик на основе языка документа. При `language: ru` — использовать `RU_STOP_WORDS` и `CFG_NOUN_PHRASE_GRAMMARS`; при `null`/`en` — текущее поведение `EN_STOP_WORDS` / `EN_NOUN_PHRASE_GRAMMARS`. Дополнительно: автовыбор spaCy-модели по языку (P2, опционально).

## Technical Context

**Language/Version**: Python 3.11–3.13 (per project `requires-python = ">=3.11,<3.14"`)  
**Primary Dependencies**: `spacy~=3.8` (NLP-модели), `pydantic` (config validation)  
**Storage**: N/A — чистая бизнес-логика  
**Testing**: pytest, `poe test_unit` + `poe test_integration`  
**Target Platform**: Linux/macOS, CLI-based pipeline  
**Project Type**: Library/CLI (monorepo, 8 packages)  
**Performance Goals**: Нулевое влияние — логика выполняется один раз при старте пайплайна  
**Constraints**: Backward compatible — 0 regressions; `poe check` (format + lint + typecheck) обязателен  
**Scale/Scope**: Изменения в ~6 файлах, 1 пакет `graphrag` + 1 файл в `graphrag-chunking` (P2)

## Constitution Check

### Gate I: Library-First Architecture
**PASS**. Изменения внутри пакета `graphrag`, не создают новых библиотек. `stop_words.py` и `cfg_extractor.py` — существующие модули.

### Gate II: CLI Interface
**PASS**. Изменения не затрагивают CLI-интерфейсы. `graphrag index` и `graphrag query` работают без изменений.

### Gate III: Test-First (NON-NEGOCABLE)
**BLOCKING**. Перед реализацией необходимо написать failing-тесты. План включает написание unit-тестов до кода.

### Gate IV: Integration Testing
**PASS**. Изменения затрагивают NLP-пайплайн — необходимы интеграционные тесты на русском тексте с полным циклом NLP-экстракции.

### Gate V: Versioning & Change Management
**PASS**. Перед мерджем будет добавлен semversioner change entry (minor, так как добавляется новое поле).

### Summary
- 1 gating requirement: **Test-First** — блокирует начало реализации
- Все остальные gates — pass
- Complexity: низкая (инкрементальные изменения в существующих модулях)

## Project Structure

### Documentation (this feature)

```text
specs/006-language-aware-nlp-factory/
├── plan.md              # This file
├── research.md          # Phase 0 output (minimal — no unknowns)
├── data-model.md        # Phase 1 output (TextAnalyzerConfig fields)
├── quickstart.md        # Phase 1 output (config examples)
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root) — files to modify

```text
packages/graphrag/graphrag/
├── config/
│   ├── defaults.py                    # FR-009: импортировать EN_NOUN_PHRASE_GRAMMARS из cfg_extractor
│   ├── enums.py                       # FR-011: обновить описание RegexEnglish
│   └── models/
│       └── extract_graph_nlp_config.py # FR-001: добавить language поле
├── index/operations/build_noun_graph/
│   └── np_extractors/
│       ├── cfg_extractor.py           # FR-008, FR-009: переименовать + вынести грамматики
│       ├── factory.py                 # FR-002, FR-005, FR-012: core logic
│       └── stop_words.py              # Уже содержит RU_STOP_WORDS — не менять
└── config/
    └── init_content.py                # FR-010: добавить language в шаблон
```

### Files to create

```text
tests/unit/
└── test_noun_phrase_factory.py   # Tests for FR-002, FR-003, FR-004
tests/unit/
└── test_cfg_extractor_language.py # Tests for FR-005, FR-006, FR-007
```

### Structure Decision
Изменения строго внутри пакета `graphrag`. Не затрагивают межпакетные API. `NounPhraseExtractorFactory` — существующий класс, расширяем, не заменяем.

## Complexity Tracking

Не применимо — нет нарушений Constitution.

## Phase 0: Research

**Результат**: NEEDS CLARIFICATION отсутствуют. Все технические решения определены в spec и этом плане.

### Decision: Добавить nullable поле `language` в `TextAnalyzerConfig`
**Rationale**: Pydantic `str | None` с `default=None` обеспечивает backward compatibility. Существующие конфиги без поля будут работать как раньше.
**Alternatives**: 
- Enum вместо str: избыточно — enum усложняет валидацию для расширяемого списка языков
- Отдельное поле `use_russian`: не масштабируемо, не поддерживает другие языки

### Decision: Language → Stop Words mapping: только `ru` → `RU_STOP_WORDS`
**Rationale**: `RU_STOP_WORDS` уже определён и проверен. Для других языков — fallback на EN. Не создаём стоп-слова для языков, которые не используются.
**Alternatives**: 
- Поддержка всех языков spaCy: избыточно для первого релиза
- Auto-detect language из модели: ненадёжно (spaCy модель ≠ язык документа)

### Decision: CFG grammars merge: base first, user overrides
**Rationale**: Позволяет пользователю переопределить конкретные правила, не указывая все заново. Соответствует паттерну pydantic config merge.

### Decision: Auto spaCy model selection — mapping dict with fallback
**Rationale**: `{"ru": "ru_core_news_md", "xx": "xx_ent_wiki_sm", default: "en_core_web_md"}` — простой, предсказуемый, легко расширяемый.

## Phase 1: Design & Contracts

### Data Model: `TextAnalyzerConfig` changes

**Existing fields** (unchanged):
- `extractor_type: NounPhraseExtractorType`
- `model_name: str` (default: `"en_core_web_md"`)
- `nlp_model: str | None`
- `max_word_length: int`
- `word_delimiter: str`
- `include_named_entities: bool`
- `exclude_nouns: list[str] | None`
- `exclude_entity_tags: list[str]`
- `exclude_pos_tags: list[str]`
- `noun_phrase_tags: list[str]`
- `noun_phrase_grammars: dict[str, str]`

**New field** (FR-001):
- `language: str | None` — Document language for selecting stop words and CFG grammars. Supported: `en` (default), `ru`. Others fall back to English behavior.

**Behavior changes** (internal, not visible in schema):
- `exclude_nouns` default: when `None` and `language == "ru"` → `RU_STOP_WORDS`, else `EN_STOP_WORDS`
- `noun_phrase_grammars` default: when empty and `language == "ru"` → `CFG_NOUN_PHRASE_GRAMMARS`, else `EN_NOUN_PHRASE_GRAMMARS`
- `nlp_model` auto-select: when both `nlp_model` and `model_name` are unset → `LANGUAGE_MODEL_MAP[language]`

### Contract: NounPhraseExtractorFactory API

**No breaking changes** to public API. The `get_np_extractor(config: TextAnalyzerConfig)` signature remains identical. Only internal behavior changes based on the new `language` field.

**Backward compatibility guarantee**:
- `language = None` (default) → identical to current behavior
- `language = "en"` → identical to current behavior  
- `exclude_nouns` explicitly set → bypasses language-based selection entirely

### Quickstart: Configuration Examples

**Minimal Russian config**:
```yaml
extract_graph_nlp:
  text_analyzer:
    extractor_type: syntactic_parser
    language: ru
    model_name: ru_core_news_md
```

**CFG extractor with auto-grammars**:
```yaml
extract_graph_nlp:
  text_analyzer:
    extractor_type: cfg
    language: ru
    model_name: ru_core_news_md
    # grammars auto-selected from CFG_NOUN_PHRASE_GRAMMARS
```

**Override stop words** (bypasses language-based selection):
```yaml
extract_graph_nlp:
  text_analyzer:
    extractor_type: syntactic_parser
    language: ru
    model_name: ru_core_news_md
    exclude_nouns: ["И", "ЧТО", "CUSTOM_WORD"]  # user-defined, language ignored
```

### Agent context update

Run the agent context update script to register new patterns for future AI-assisted development.
