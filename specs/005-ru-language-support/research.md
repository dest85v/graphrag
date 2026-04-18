# Implementation Plan: Поддержка русского языка с вкраплениями англоязычных терминов

**Branch**: `005-ru-language-support` | **Date**: 2026-04-17 | **Spec**: [spec.md](../spec.md)
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

**Результат**: Все gates пройдены. Violations: нет.

## Project Structure

### Documentation (this feature)

```text
specs/005-ru-language-support/
├── plan.md              # Этот файл
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code Changes (repository root)

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

packages/graphrag/graphrag/
└── index/operations/build_noun_graph/np_extractors/
    ├── regex_extractor.py              # КРИТИЧЕСКИ: Unicode-aware _is_valid_token()
    └── stop_words.py                   # Добавить: RU_STOP_WORDS
tests/
├── unit/
│   └── index/operations/build_noun_graph/
│       └── test_regex_extractor_unicode.py  # Новые unit-тесты
└── integration/
    └── test_nlp_multilingual.py               # Новые integration-тесты
```

**Structure Decision**: Изменения коснутся преимущественно пакета `graphrag` (NLP-экстракторы + конфигурация). Пакет `graphrag-chunking` не меняется (token-based chunking не зависит от языка). Интеграционные тесты в `tests/` на корневом уровне.

## Phase 0: Research

### Resolved Technical Decisions

**Decision 1**: Regex-паттерн для валидации токенов

- **Выбрано**: `r"^\w+[\-]?\w*$"` с флагом `re.UNICODE` (или `re.ASCII` не передавать)
- **Почему**: `\w` с Unicode включает кириллицу, латиницу, цифры, подчёркивание — все допустимые символы для именных фраз. Дефис поддерживается явно для compound-слов ("deployment-pipeline").
- **Альтернативы**:
  - `re.UNICODE` + `\p{L}+` (Unicode property escapes) — не поддерживается в Python stdlib `re`, требует `regex` библиотеки (доп. зависимость). **Отклонено**.
  - Явный набор диапазонов Unicode — избыточен, `\w` покрывает все нужные случаи. **Отклонено**.
  - Сохранение ASCII-only + доп. паттерн для кириллицы — усложняет код, нарушает DRY. **Отклонено**.

**Decision 2**: NLP-модель по умолчанию

- **Выбрано**: Сохранить `en_core_web_md` как default для обратной совместимости. Добавить поле `nlp_model: str | None = None` в `TextAnalyzerConfig`. Если `None` — использовать дефолт из `defaults.py`.
- **Почему**: Any breaking change в default поведении нарушит существующие проекты. Явное указание новой модели пользователем — безопасный путь.
- **Альтернативы**:
  - Сменить default на `xx_ent_wiki_sm` — нарушит backward compat. **Отклонено**.
  - Добавить флаг `--enable-russian` в CLI — излишняя сложность, конфиг гибче. **Отклонено**.

**Decision 3**: Опциональные зависимости

- **Выбрано**: `[nlp-ru] = ["spacy-ru-core-news-md~=3.8"]`, `[nlp-xx] = ["spacy-xx-ent-wiki-sm~=3.8"]` в `pyproject.toml`.
- **Почему**: Пользователь может установить одну команду `uv add graphrag[nlp-ru]`. spaCy модели доступны как pip-пакеты.
- **Альтернативы**:
  - Встроить модели в пакет — увеличит размер дистрибутива. **Отклонено**.
  - `spacy download` в init-скрипте — не работает offline, не детерминированно. **Отклонено**.

**Decision 4**: Stop-words для русского языка

- **Выбрано**: Добавить `RU_STOP_WORDS` в `stop_words.py`. Не делать обязательным — если `exclude_nouns=None`, использовать `EN_STOP_WORDS` как fallback (текущее поведение).
- **Почему**: Backward compat + не блокирует реализацию. Пользователь может передать кастомный стоп-лист через конфиг.
- **Альтернативы**:
  - Использовать spaCy встроенные stop words (`nlp.Defaults.stop_words`) — может быть неполным. **Принято как fallback**.

### research.md

```markdown
# Research: Russian Language Support in GraphRAG

## Decision: Unicode-aware token validation in RegexExtractor

**Decision**: Replace `_is_valid_token()` regex from `^[a-zA-Z0-9\-]+$` to `^\w+[\-]?\w*$` with `re.UNICODE`.

**Rationale**: 
- `\w` with Unicode flag matches any Unicode word character: Cyrillic, Latin, digits, underscore.
- Explicit hyphen support for compound words ("deployment-pipeline").
- No new dependencies — uses stdlib `re` module.
- Tested: `re.match(r"^\w+[\-]?\w*$", "внутренний")` → matches.
- `re.match(r"^\w+[\-]?\w*$", "API")` → matches.
- `re.match(r"^\w+[\-]?\w*$", "настройка API")` → no match (spaces handled by noun_chunks, not individual tokens).

**Alternatives considered**:
- `\p{L}+` (Unicode property escapes): Requires `regex` third-party library. **Rejected** — adds dependency.
- Explicit Unicode ranges: Overly verbose. **Rejected**.
- ASCII-only + Cyrillic fallback: Dual-path logic, DRY violation. **Rejected**.

## Decision: Configurable NLP model with backward-compatible default

**Decision**: Add `nlp_model: str | None = None` field to `TextAnalyzerConfig`. Default from `defaults.py` (`en_core_web_md`) unchanged.

**Rationale**:
- Any behavior change without explicit config would break existing projects.
- `None` → use `defaults.extract_graph_nlp.text_analyzer.model_name`.
- Explicit string → use that model name (with auto-download via `spacy.cli.download`).
- Existing factory pattern already accepts `model_name` in all extractor constructors.

**Alternatives considered**:
- Change default to `xx_ent_wiki_sm`: Breaks backward compat. **Rejected**.
- CLI flag `--enable-russian`: Less flexible than YAML config. **Rejected**.

## Decision: Optional extras for Russian spaCy models

**Decision**: 
```toml
[project.optional-dependencies]
nlp-ru = ["spacy-ru-core-news-md~=3.8"]
nlp-xx = ["spacy-xx-ent-wiki-sm~=3.8"]
```

**Rationale**:
- `uv add graphrag[nlp-ru]` installs model in one command.
- spaCy models available as pip packages (spacy-locales / direct from GitHub).
- No embedding models in package — keeps distribution size small.

**Alternatives considered**:
- Embed models in package: Increases dist size by ~100MB. **Rejected**.
- `spacy download` in init script: Requires internet, non-deterministic. **Rejected**.

## Decision: Russian stop words

**Decision**: Add `RU_STOP_WORDS` list to `stop_words.py`. If `exclude_nouns=None`, use `EN_STOP_WORDS` as fallback.

**Rationale**:
- spaCy has built-in `nlp.Defaults.stop_words` per model — may be sufficient.
- Custom RU stop words improve quality but are not critical for MVP.
- User can pass custom stop words via config.

**Alternatives considered**:
- Auto-detect language and use model-specific stop words: Complex, adds runtime overhead. **Deferred**.