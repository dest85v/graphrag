# Feature Specification: NLTK Multilingual Sentence Tokenizer для chunking

**Feature Branch**: `007-multilingual-sentence-tokenizer`  
**Created**: 2026-04-18  
**Status**: Draft  
**Input**: User description: "Надо реализовать задачу 'P2 — NLTK Multilingual Sentence Tokenizer для chunking'"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Русскоязычный документ с sentence chunking (Priority: P1)

Пользователь загружает русскоязычный документ и хочет разбить его на предложения через `chunking.type: sentence`. Сейчас `nltk.sent_tokenize()` всегда использует английскую модель PUNKT, которая плохо разбирает русские предложения (особенно с сокращениями, аббревиатурами, инициалами).

**Why this priority**: Это ядро проблемы — без мультиязычного токенизатора sentence chunking для не-английских текстов даёт качественные деградации. Пользователи с русскоязычными документами получают некорректные чанки.

**Independent Test**: Можно запустить `graphrag index` с `chunking.type: sentence` + `nltk_language: russian` на русском тексте и проверить, что предложения разбиты корректно (сравнить с ручным разбиением).

**Acceptance Scenarios**:

1. **Given** конфиг `chunking.type: sentence` и `nltk_language: russian`, **When** обрабатывается текст `«Иван Иванович пришёл на работу в понедельник. Он открыл ноутбук и начал анализ данных.»`, **Then** текст разбивается на 2 предложения: `«Иван Иванович пришёл на работу в понедельник.»` и `«Он открыл ноутбук и начал анализ данных.»`
2. **Given** конфиг `chunking.type: sentence` и `nltk_language: english` (дефолт), **When** обрабатывается тот же текст, **Then** текст разбивается как минимум на 2 предложения (возможно с деградацией качества)

---

### User Story 2 — Английский текст сохраняет текущее поведение (Priority: P1)

Пользователь с англоязычными документами не хочет никаких изменений. Текущее поведение `nltk.sent_tokenize()` без явного языка должно сохраняться как дефолт.

**Why this priority**: Backward compatibility — текущие пайплайны не должны сломаться.

**Independent Test**: Запустить существующие тесты и пайплайн с англоязычными документами — поведение идентично.

**Acceptance Scenarios**:

1. **Given** конфиг не содержит `nltk_language` (или `nltk_language: english`), **When** обрабатывается английский текст, **Then** результат идентичен текущему поведению без изменений
2. **Given** существующий `config.yaml` без поля `nltk_language`, **When** запускается `graphrag index`, **Then** используется `english` по умолчанию — никаких ошибок, никаких изменений в output

---

### User Story 3 — Поддержка других языков (Priority: P2)

Пользователь хочет использовать sentence chunking для немецкого, французского, испанского и других поддерживаемых NLTK PUNKT языков.

**Why this priority**: Расширяет поддержку мультиязычных документов. Не блокирует основной сценарий (RU + EN), но важно для international пользователей.

**Independent Test**: Установить NLTK Punkt модель для нужного языка, запустить sentence chunking с соответствующим `nltk_language`.

**Acceptance Scenarios**:

1. **Given** `nltk_language: german`, **When** обрабатывается немецкий текст, **Then** предложения разбиваются корректно
2. **Given** `nltk_language: french`, **When** обрабатывается французский текст, **Then** предложения разбиваются корректно
3. **Given** `nltk_language: unsupported_language`, **When** обрабатывается текст, **Then** падает с понятной ошибкой от NLTK (Unknown punkt language)

---

### Edge Cases

- Что происходит при `nltk_language: ""` (пустая строка)? → Дефолт `english`
- Что происходит при `nltk_language: null`? → Дефолт `english`
- Что если NLTK punkt модель для указанного языка не скачана? → NLTK auto-downloads при первом вызове `sent_tokenize()`
- Что если текст содержит смешанные языки (RU + EN)? → Используется модель для указанного языка, не-указанный язык может обрабатываться с деградацией
- Как ведёт себя `bootstrap()` — скачивает ли он языковые модели автоматически? → Нет, скачивает только `punkt` и `punkt_tab`. Языковые модели внутри `punkt_tab` загружаются автоматически при вызове `sent_tokenize(language=...)`

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `ChunkingConfig` MUST have an optional `nltk_language` field with default value `"english"`
- **FR-002**: `SentenceChunker.__init__()` MUST accept `nltk_language` parameter and pass it to `nltk.sent_tokenize(language=...)`
- **FR-003**: `nltk.sent_tokenize()` MUST be called with `language=self._nltk_language` instead of the default English-only
- **FR-004**: The `nltk_language` config field MUST be passed from `ChunkingConfig` through `create_chunker()` to `SentenceChunker` via `**kwargs`
- **FR-005**: `ChunkingDefaults` in the main graphrag config MUST include `nltk_language: "english"` as default
- **FR-006**: The `init_content.py` config template MUST include `nltk_language` field in the `chunking` section with documentation comment
- **FR-007**: Default value MUST be `"english"` to preserve backward compatibility with existing configs
- **FR-008**: The `bootstrap_nltk.py` MUST continue downloading `punkt` and `punkt_tab` (already correct, no changes needed)
- **FR-009**: Invalid language values MUST fail gracefully with NLTK's built-in error (no custom error handling needed)

### Key Entities

- **ChunkingConfig**: Pydantic model that holds chunking parameters. ADDS `nltk_language: str` field.
- **SentenceChunker**: Chunker implementation that splits text into sentence-based chunks. MODIFIED to accept and use `nltk_language` parameter.
- **ChunkingDefaults**: Dataclass with default chunking values. ADDS `nltk_language: str` field.
- **NLTK Punkt**: Sentence tokenizer library. Already present, multilingual models available in `punkt_tab` package (NLTK 3.9+).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Russian text `«Иван Иванович пришёл на работу в понедельник. Он открыл ноутбук.»` MUST be split into exactly 2 sentences when `nltk_language: russian` is configured
- **SC-002**: Existing English-only configs (without `nltk_language` field) MUST produce identical output to pre-change behavior (zero regression)
- **SC-003**: All existing unit and integration tests MUST pass without modification (backward compatibility verified)
- **SC-004**: `poe check` (format + lint + typecheck) MUST pass after implementation

## Assumptions

- NLTK 3.9+ is already installed (confirmed in `packages/graphrag/pyproject.toml:49`: `nltk~=3.9`) — supports `sent_tokenize(language=...)` since 3.8.2
- `punkt_tab` package (already downloaded by `bootstrap()`) contains multilingual Punkt models for Russian, German, French, Spanish, and other languages
- The `nltk_language` field will be added via `extra="allow"` in `ChunkingConfig.model_config` — no pydantic validation errors for unknown fields
- Language model auto-download by NLTK on first use is acceptable behavior (models cached in `~/.nltk/`)
- The `chunking.type: tokens` default means this feature only affects users who explicitly set `chunking.type: sentence`
