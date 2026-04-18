# Implementation Plan: Поддержка русского языка с вкраплениями англоязычных терминов

**Branch**: `005-ru-language-support` | **Date**: 2026-04-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-ru-language-support/spec.md`

## Summary

Добавить поддержку обработки русскоязычных документов и смешанного RU+EN текста в GraphRAG. Текущая реализация использует spaCy-модель `en_core_web_md` по умолчанию и ASCII-only regex для валидации токенов, что полностью блокирует обработку кириллического текста. Решение включает: Unicode-aware валидацию токенов в RegexExtractor, настраиваемую NLP-модель через конфигурацию, опциональные зависимости для русскоязычных spaCy-моделей, и интеграционные тесты.

## Technical Context

**Language/Version**: Python 3.11–3.13  
**Primary Dependencies**: `spacy~=3.8` (уже в зависимостях), `tiktoken~=0.8` (o200k_base tokenizer, поддерживает Unicode)  
**Storage**: N/A — pure library package  
**Testing**: pytest с asyncio_mode="auto", 1000s timeout. Пять тестовых суит: unit, integration, smoke, notebook, verbs  
**Target Platform**: Linux server, кроссплатформенная библиотека  
**Project Type**: Библиотека (монолитный monorepo из 8 пакетов, управляемый uv)  
**Performance Goals**: Не более 20% регрессии по сравнению с ASCII-режимом на английских текстах (SC-005)  
**Constraints**: Обратная совместимость обязательна — поведение по умолчанию не должно меняться. Все PR должны проходить `uv run poe check` (Ruff + pyright).  
**Scale/Scope**: 3 пакета: `graphrag` (конфиг, NLP-экстракторы), `graphrag-chunking` (не меняется), `graphrag` (pyproject.toml — опциональные зависимости)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Принцип | Проверка | Статус |
|---------|----------|--------|
| **I. Library-First Architecture** | Изменения в пакете `graphrag` — NLP-экстракторы уже являются независимыми компонентами. Конфигурационные изменения остаются в рамках существующих пакетов. | ✅ compliant |
| **II. CLI Interface** | CLI-интерфейс не меняется. Выбор NLP-модели настраивается через `graphrag.yaml` конфиг, а не CLI-флаги. | ✅ compliant |
| **III. Test-First (NON-NEGOTIABLE)** | Все изменения должны сопровождаться unit + integration тестами, написанными ДО реализации. | ⚠️ будет enforced при реализации |
| **IV. Integration Testing** | Новые тесты на смешанный RU+EN текст, три NLP-модели, автоскачивание моделей. | ✅ в плане |
| **V. Versioning & Change Management** | semversioner add-change будет добавлен перед merge. MINOR change, т.к. новая функциональность. | ✅ будет enforced при реализации |
| **Security & Responsible AI** | spaCy-модели скачиваются из доверенных источников (GitHub spacy-models). Нет новых API-вызовов или сетевых запросов. | ✅ compliant |

**Post-Design Re-check**: После Phase 1 дизайн не вводит новых архитектурных абстракций, изменений в CLI, или внешних зависимостей. Все изменения локальны к пакету `graphrag`. Gates пройдены.

## Project Structure

### Documentation (this feature)

```text
specs/005-ru-language-support/
├── plan.md              # Этот файл (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/
│   └── nlp-model-config.md  # Contract для nlp_model config field
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
packages/graphrag/graphrag/
├── config/
│   ├── defaults.py                    # Изменить: default NLP model name (обратная compat)
│   └── models/
│       └── extract_graph_nlp_config.py # Добавить: поле nlp_model (optional[str])
├── index/operations/build_noun_graph/
│   └── np_extractors/
│       ├── regex_extractor.py          # КРИТИЧЕСКИ: Unicode-aware _is_valid_token()
│       ├── cfg_extractor.py            # Добавить: RU grammar rules
│       └── stop_words.py               # Добавить: RU_STOP_WORDS (опционально)
packages/graphrag/
└── pyproject.toml                      # Добавить: [project.optional-dependencies] nlp-ru, nlp-xx

tests/
├── unit/
│   └── index/operations/build_noun_graph/
│       └── test_regex_extractor_unicode.py  # Новые unit-тесты
└── integration/
    └── test_nlp_multilingual.py               # Новые integration-тесты
```

**Structure Decision**: Изменения коснутся преимущественно пакета `graphrag` (NLP-экстракторы + конфигурация). Пакет `graphrag-chunking` не меняется (token-based chunking не зависит от языка). Интеграционные тесты в `tests/` на корневом уровне. Никаких новых пакетов не требуется — все изменения в рамках существующей архитектуры.

## Complexity Tracking

> No constitution violations — table empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | — | — |
