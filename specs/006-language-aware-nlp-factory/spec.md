# Feature Specification: Language-Aware NLP Factory

**Feature Branch**: `006-language-aware-nlp-factory`  
**Created**: 2026-04-18  
**Status**: Draft  
**Input**: User description: "P1 — Language-aware NLP Factory: auto-select stop words и CFG grammars по языку"

## User Scenarios & Testing

### User Story 1 — Настройка NLP-экстракции для русского текста (Priority: P1)

Пользователь работает с русскоязычными документами и настраивает GraphRAG. Он устанавливает русскую spaCy-модель (`ru_core_news_md`) и указывает язык документов как `ru`. Система автоматически подбирает русские стоп-слова и CFG-грамматики, без необходимости ручного указания.

**Why this priority**: Это основная ценность фичи — убирает ручной конфигуринг стоп-слов и грамматик. Без этого русскоязычные стоп-слова остаются английскими, что делает извлечение именных фраз некорректным.

**Independent Test**: Можно протестировать изолированно: создать конфиг с `language: ru` и `extractor_type: syntactic_parser`, запустить NLP-экстрактор на русском тексте и проверить, что русские стоп-слова (`И`, `ИЛИ`, `ЧТО`) фильтруются, а английские (`stuff`, `thing`) — нет.

**Acceptance Scenarios**:

1. **Given** пользователь указал `extract_graph_nlp.text_analyzer.language: ru` и не указал `exclude_nouns`, **When** запускается NLP-экстрактор, **Then** используются русские стоп-слова (`RU_STOP_WORDS`), а не английские
2. **Given** пользователь указал `language: ru` и `extractor_type: cfg`, **When** запускается CFG-экстрактор без пользовательских грамматик, **Then** применяются русские CFG-грамматики (`CFG_NOUN_PHRASE_GRAMMARS`)
3. **Given** пользователь явно указал `exclude_nouns: [...]`, **When** запускается NLP-экстрактор, **Then** пользовательские стоп-слова используются в обход автоподбора (переопределяют language-based выбор)

---

### User Story 2 — Backward compatibility для англоязычных документов (Priority: P1)

Пользователь с текущим английским конфигом не замечает изменений. При `language: null` или отсутствии поля система ведёт себя как раньше — использует английские стоп-слова и грамматики по умолчанию.

**Why this priority**: Любое breaking change для существующих пользователей неприемлемо. Backward compatibility — критичное требование.

**Independent Test**: Запустить существующий английский конфиг без поля `language` — убедиться, что поведение идентично текущему (EN_STOP_WORDS, EN_NOUN_PHRASE_GRAMMARS).

**Acceptance Scenarios**:

1. **Given** конфиг без поля `language` (null), **When** создаётся NLP-экстрактор, **Then** используется `EN_STOP_WORDS` (текущее поведение)
2. **Given** конфиг с `language: en`, **When** создаётся NLP-экстрактор, **Then** используется `EN_STOP_WORDS`

---

### User Story 3 — Автовыбор spaCy-модели по языку (Priority: P2)

Пользователь указывает только `language: ru`, не указывая `model_name`. Система автоматически выбирает `ru_core_news_md`. Если язык неизвестен — fallback на `xx_ent_wiki_sm` (мультиязычная).

**Why this priority**: Снижает порог входа — пользователю не нужно знать имена spaCy-моделей. Но это опционально, так как `nlp_model` уже поддерживается.

**Independent Test**: Установить `language: ru` без `nlp_model` — проверить, что effective model name = `ru_core_news_md`.

**Acceptance Scenarios**:

1. **Given** `language: ru` и не указан `nlp_model`, **When** создаётся экстрактор, **Then** `effective_model_name` = `ru_core_news_md`
2. **Given** `language: de` и не указан `nlp_model`, **When** создаётся экстрактор, **Then** `effective_model_name` = `de_core_news_md`
3. **Given** `language: xx` и не указан `nlp_model`, **When** создаётся экстрактор, **Then** `effective_model_name` = `xx_ent_wiki_sm`

---

### Edge Cases

- Пользователь указал `language: ru`, но `ru_core_news_md` не установлена — система должна вывести понятную ошибку при старте (а не crash при первом вызове)
- Пользователь указал `language: ru` но `extractor_type: regex_english` — предупреждение, что regex_english ограничен английским
- Пустая строка `language: ""` — обрабатывается как fallback на `en`

## Requirements

### Functional Requirements

- **FR-001**: Система ДОЛЖНА добавлять поле `language` в конфигурацию `TextAnalyzerConfig` с валидацией типа `str | None`
- **FR-002**: При `language: ru` и незаданном `exclude_nouns`, NLP-экстрактор ДОЛЖЕН использовать `RU_STOP_WORDS` вместо `EN_STOP_WORDS`
- **FR-003**: При `language: en` или `language: null` и незаданном `exclude_nouns`, система ДОЛЖНА использовать `EN_STOP_WORDS` (backward compatibility)
- **FR-004**: Пользовательский `exclude_nouns` ДОЛЖЕН переопределять language-based автоподбор
- **FR-005**: CFG-экстрактор ДОЛЖЕН автоматически применять `CFG_NOUN_PHRASE_GRAMMARS` при `language: ru` и незаданных пользовательских грамматиках
- **FR-006**: CFG-экстрактор ДОЛЖЕН применять `EN_NOUN_PHRASE_GRAMMARS` при `language: en` или `language: null`
- **FR-007**: Пользовательские грамматики ДОЛЖНЫ мержиться с базовыми: базовые → пользовательские (переопределяют)
- **FR-008**: `RU_NOUN_PHRASE_GRAMMARS` в `cfg_extractor.py` ДОЛЖЕН быть переименован в `CFG_NOUN_PHRASE_GRAMMARS`
- **FR-009**: Английские грамматики ДОЛЖНЫ быть вынесены из `defaults.py` в `cfg_extractor.py` как `EN_NOUN_PHRASE_GRAMMARS`
- **FR-010**: Файл `init_content.py` ДОЛЖЕН включать поле `language` в шаблон конфигурации с описанием поддерживаемых языков
- **FR-011**: Enum `NounPhraseExtractorType.RegexEnglish` ДОЛЖЕН быть обновлён с указанием ограничения по языку
- **FR-012**: При `language: ru` и незаданном `nlp_model` (опционально), система ДОЛЖНА предложить `ru_core_news_md` как default model name

### Key Entities

- **TextAnalyzerConfig**: Конфигурация NLP-текстоанализатора. Ключевое изменение: добавление поля `language` (`str | None`)
- **NounPhraseExtractorFactory**: Фабрика создания экстракторов. Ключевое изменение: логика автоподбора стоп-слов и грамматик на основе `language`
- **RU_STOP_WORDS**: Множество русских стоп-слов, определённых в `stop_words.py` — используется при `language: ru`
- **RU_NOUN_PHRASE_GRAMMARS** (→ `CFG_NOUN_PHRASE_GRAMMARS`): CFG-грамматики для русского языка, определённые в `cfg_extractor.py` — используются CFG-экстрактором при `language: ru`
- **EN_NOUN_PHRASE_GRAMMARS**: CFG-грамматики по умолчанию (английские), вынесены из `defaults.py`
- **CFG_NounPhraseExtractor**: CFG-экстрактор — должен использовать language-based грамматики при отсутствии пользовательских

## Success Criteria

### Measurable Outcomes

- **SC-001**: При настройке `language: ru` с `extractor_type: syntactic_parser` — русские стоп-слова (`И`, `ИЛИ`, `ЧТО`) фильтруются из извлечённых именных фраз, английские (`stuff`, `thing`) — нет
- **SC-002**: Существующие конфигурации без поля `language` работают идентично текущему поведению (0 regressions)
- **SC-003**: При `extractor_type: cfg` + `language: ru` — CFG-экстрактор применяет `CFG_NOUN_PHRASE_GRAMMARS` вместо английских грамматик
- **SC-004**: 100% существующих unit-тестов проходят без изменений
- **SC-005**: Пользовательский `exclude_nouns: [...]` полностью переопределяет language-based автоподбор (проверяется логированием/тестом)

## Assumptions

- `RU_STOP_WORDS` и `RU_NOUN_PHRASE_GRAMMARS` уже определены в коде и не требуют создания
- spaCy-модель `ru_core_news_md` должна быть установлена пользователем отдельно (не распространяется с пакетом)
- Язык определяется по коду/имени модели spaCy: `ru` → `ru_core_news_md`, `xx` → `xx_ent_wiki_sm`
- Поддерживаемые языки на начальном этапе: `en` (default), `ru` — остальные языки получают fallback на `en`
- Поле `language` является опциональным (nullable) для обеспечения backward compatibility
- Мерж пользовательских грамматик с базовыми: базовые применяются первыми, пользовательские переопределяют ключи
