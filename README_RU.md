# GraphRAG — Использование с русским языком

Инструкция по настройке GraphRAG для обработки русскоязычных документов с вкраплениями англоязычных терминов (API, deployment pipeline, machine learning и т.д.).

## Кратко: минимальная конфигурация

```yaml
chunking:
  type: tokens
  size: 1200
  overlap: 100

extract_graph_nlp:
  text_analyzer:
    extractor_type: syntactic_parser
    model_name: ru_core_news_md

extract_graph:
  prompt: "prompts/extract_graph.txt"
  entity_types: [organization, person, geo, event, technology, product, concept]
  max_gleanings: 1
```

## Установка русской spaCy-модели

```bash
python -m spacy download ru_core_news_md
```

> **Альтернатива:** `xx_ent_wiki_sm` — мультиязычная модель (лучше для смешанного RU+EN текста, но менее точна для чистого русского).
>
> ```bash
> python -m spacy download xx_ent_wiki_sm
> ```

## Настройка по шагам

### 1. Инициализация проекта

```bash
graphrag init --root ./my-project --force
```

### 2. Настройка chunking

**Рекомендуется:** `type: tokens` — не зависит от языка.

```yaml
chunking:
  type: tokens    # language-agnostic, работает для любого языка
  size: 1200
  overlap: 100
```

Если нужен `type: sentence` — по умолчанию NLTK punkt работает только на английском. Для русского:

```yaml
chunking:
  type: sentence
  nltk_language: russian  # требует NLTK 3.9+
  size: 1200
  overlap: 100
```

### 3. Настройка NLP-экстрактора сущностей

#### Вариант A: Syntactic Parser (рекомендуется для русского)

Использует dependency parsing + NER от spaCy. Корректно работает с любым языком при подстановке соответствующей модели.

```yaml
extract_graph_nlp:
  text_analyzer:
    extractor_type: syntactic_parser
    model_name: ru_core_news_md  # русская модель spaCy
    include_named_entities: true
    max_word_length: 15
```

#### Вариант B: CFG Extractor

Использует CFG-грамматики поверх POS-тегов spaCy. Быстрее syntactic_parser, но грамматики нужно настраивать под язык.

```yaml
extract_graph_nlp:
  text_analyzer:
    extractor_type: cfg
    model_name: ru_core_news_md
    include_named_entities: true
    # Grammars задаются через конфигурацию (см. ниже)
```

#### Вариант C: Regex Extractor (по умолчанию, только английский)

```yaml
extract_graph_nlp:
  text_analyzer:
    extractor_type: regex_english  # НЕ подходит для русского
```

`regex_english` использует `en_core_web_md` и regex-валидацию токенов. Для русского языка **не подходит**.

### 4. Prompt-tune (рекомендуется)

Автогенерация промптов на основе ваших документов. LLM определит язык и создаст промпты на русском.

```bash
graphrag prompt_tune --root ./my-project --max-observations 25 --domain "Технологии"
```

Что делает prompt-tune:
- Определяет язык документов (русский)
- Генерирует список entity types на основе текстов
- Создаёт `prompts/extract_graph.txt` с инструкциями на русском
- Описания сущностей будут на русском, названия — в оригинале

Результат:

```
my-project/
├── config.yaml
└── prompts/
    ├── extract_graph.txt          # ← сгенерирован на русском
    ├── entity_summarization_prompt.txt
    ├── community_report_text.txt
    └── ...
```

После prompt-tune проверьте `prompts/extract_graph.txt` — в шагах должно быть `Return output in Russian`.

### 5. Полная конфигурация: пример

```yaml
# LLM
completion_models:
  default_completion_model:
    model_provider: openai
    model: gpt-4.1
    auth_method: api_key
    api_key: ${GRAPHRAG_API_KEY}

embedding_models:
  default_embedding_model:
    model_provider: openai
    model: text-embedding-3-large
    auth_method: api_key
    api_key: ${GRAPHRAG_API_KEY}

# Input
input:
  type: text

# Chunking — токен-базированный (language-agnostic)
chunking:
  type: tokens
  size: 1200
  overlap: 100

# NLP — русская модель + syntactic parser
extract_graph_nlp:
  text_analyzer:
    extractor_type: syntactic_parser
    model_name: ru_core_news_md
    include_named_entities: true
    max_word_length: 15
    exclude_entity_tags: [DATE]
    exclude_pos_tags: [DET, PRON, INTJ, X]

# Graph extraction — промпт сгенерирован prompt-tune
extract_graph:
  completion_model_id: default_completion_model
  prompt: "prompts/extract_graph.txt"
  entity_types: [organization, person, geo, event, technology, concept]
  max_gleanings: 1

# Vector store
vector_store:
  type: lancedb
  db_uri: "./output/lancedb"

# Storage
input_storage:
  type: file
  base_dir: "input"
output_storage:
  type: file
  base_dir: "output"
reporting:
  type: file
  base_dir: "logs"
cache:
  type: json
  storage:
    type: file
    base_dir: "cache"
```

## Индексация и запросы

```bash
# Индексация
graphrag index --root ./my-project

# Локальный поиск
graphrag query --root ./my-project --method local --query "Что такое машинное обучение?"

# Глобальный поиск
graphrag query --root ./my-project --method global --query "Какие технологии описаны в документах?"
```

## Выбор spaCy-модели

| Модель | Язык | Размер | Когда использовать |
|---|---|---|---|
| `ru_core_news_md` | Русский | ~30 МБ | Чистый русский текст, максимальная точность |
| `xx_ent_wiki_sm` | Мультиязычный | ~12 МБ | Смешанный RU+EN текст, именованные сущности |
| `en_core_web_md` | Английский | ~30 МБ | Только английский текст (по умолчанию) |

Скачать:
```bash
python -m spacy download ru_core_news_md
python -m spacy download xx_ent_wiki_sm
```

## Смешанный RU+EN текст

При обработке документов типа:

> "Модель машинного обучения обучалась на данных в облачном deployment pipeline с использованием Kubernetes и API-эндрпоинтов."

GraphRAG:
- **Токенизация:** `o200k_base` корректно токенизирует и кириллицу, и латиницу
- **NLP-экстрактор:** `ru_core_news_md` извлечёт русские noun phrases; английские термины (API, Kubernetes, deployment pipeline) также будут распознаны как сущности
- **LLM-экстракция:** сохранит названия сущностей в оригинале (Kubernetes, API), описания — на русском
- **Embeddings:** multilingual-модели (text-embedding-3-large) кодируют и русский, и английский

## Отладка

### Проверка модели spaCy

```python
import spacy
nlp = spacy.load("ru_core_news_md")
doc = nlp("Модель машинного обучения работает в облаке.")
print([(token.text, token.pos_, token.dep_) for token in doc])
# [('Модель', 'NOUN', 'nsubj'), ('машинного', 'NOUN', 'nmod'), ...]

doc = nlp("The API endpoint is deployed in the cloud.")
print([(token.text, token.pos_, token.dep_) for token in doc])
# [('The', 'DET', 'det'), ('API', 'NOUN', 'compound'), ...]
```

### Проверка stop words

```python
from graphrag.index.operations.build_noun_graph.np_extractors.stop_words import (
    EN_STOP_WORDS,
    RU_STOP_WORDS,
)
print(RU_STOP_WORDS)
# {'И', 'ИЛИ', 'НО', 'В', 'НА', 'ЧТО', 'КОТОРЫЙ', ...}
```

### Визуализация графа

```bash
# После индексации — файлы в output/
ls output/
# artifacts/graph/**.graphml — граф в формате GraphML
```

## Возможные проблемы

### НLP-экстрактор не извлекает русские фразы

Проверьте:
1. `extractor_type: syntactic_parser` (не `regex_english`)
2. Модель: `model_name: ru_core_news_md` (не `en_core_web_md`)
3. Модель установлена: `python -m spacy download ru_core_news_md`

### Предложения разбиваются некорректно при `type: sentence`

Перейдите на `type: tokens`:

```yaml
chunking:
  type: tokens  # вместо sentence
```

### Entity descriptions переведены не на русский

Запустите `prompt_tune` ещё раз с правильным доменом:

```bash
graphrag prompt_tune --root ./my-project --max-observations 50
```

### Английские термины теряются при извлечении сущностей

Это нормально для `ru_core_news_md` — модель лучше понимает русские фразы. Английские термины в виде отдельных слов (API, Kubernetes) обычно распознаются. Если нужно лучше распознавать EN-термины в RU-тексте — попробуйте `xx_ent_wiki_sm`.
