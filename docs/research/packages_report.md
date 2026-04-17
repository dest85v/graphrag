# GraphRAG — Packages Research Report

Алгоритмы и ядро логики всех 8 пакетов монорепозитория.

---

## Обзор пакетов

| Пакет | Назначение | Зависимости |
|---|---|---|
| `graphrag-common` | Базовый Factory ABC, утилиты хеширования, загрузки конфигов | pydantic, pyyaml, toml, python-dotenv |
| `graphrag-chunking` | Стратегии чанкинга документов | graphrag-common, pydantic, nltk |
| `graphrag-input` | Загрузка документов из разных форматов | graphrag-common, graphrag-storage, pydantic, markitdown, pyarrow |
| `graphrag-storage` | Бэкенды хранения и табличные провайдеры | graphrag-common, pydantic, azure-*, aiofiles, pandas |
| `graphrag-cache` | Кэш для конвейера индексации | graphrag-common, graphrag-storage |
| `graphrag-llm` | Абстракции LLM: коммитменты, эмбеддинги, middleware | graphrag-cache, graphrag-common, litellm, pydantic |
| `graphrag-vectors` | Векторные хранилища и DSL фильтрации | graphrag-common, pydantic, lancedb, azure-*, numpy |
| `graphrag` | Основной пакет: индексация, запросы, CLI | все 7 подпакетов |

---

## 1. graphrag-common — Factory Pattern и Утилиты

**Путь:** `packages/graphrag-common/graphrag_common/`

### Factory[T] — Generic Factory ABC

`factory.py:26-113` — Базовый класс-синглтон для регистрации и создания реализаций по имени стратегии.

- **register(strategy, initializer, scope)** — `factory.py:51`: Регистрирует стратегию с инициализатором
- **scope** — `Singleton` (кэшируется по хешу аргументов) или `Transient` (создаётся каждый раз)
- **create(strategy, init_args)** — `factory.py:73`: Ленивое создание с кэшированием для Singleton
- **hash_data()** — `hasher/`: Хеширование аргументов для кэша синглтонов

### Загрузка конфигов

`config/` — Загрузка YAML/TOML конфигов через pyyaml и toml библиотеки.

---

## 2. graphrag-chunking — Чанкинг Документов

**Путь:** `packages/graphrag-chunking/graphrag_chunking/`

### SentenceChunker — Чанкинг по предложениям

`sentence_chunker.py:17-48`

1. Разбивает текст на предложения через `nltk.sent_tokenize()`
2. Корректирует символьные смещения для учёта пробелов (lines 36-47)

### TokenChunker — Чанкинг по токенам

`token_chunker.py:14-69`

Скользящее окно по токенам:
1. Кодирует текст в токены через переданную `encode()` callable (line 54)
2. Создаёт чанки размером `chunk_size` с перекрытием `chunk_overlap` (lines 56-68)
3. Декодирует токены обратно в текст через `decode()` callable (line 61)

`split_text_on_tokens()` — `token_chunker.py:45-69`: Алгоритм скользящего окна по массиву токенов.

### ChunkerFactory

`chunker_factory.py:15-77` — Factory по паттерну из graphrag-common. Авто-регистрация `TokenChunker` и `SentenceChunker` по `ChunkerType` enum.

---

## 3. graphrag-input — Загрузка Документов

**Путь:** `packages/graphrag-input/graphrag_input/`

### InputReader — ABC для чтения документов

Определяет интерфейс: `read()` возвращает async iterator `TextDocument` объектов (id, text, title, metadata).

### Форматные ридеры

`input_reader_factory.py:20-94`:

| Ридер | Формат |
|---|---|
| `CSVFileReader` | CSV с настраиваемыми текстовым/ID столбцами |
| `TextFileReader` | Plain text |
| `JSONFileReader` | JSON |
| `JSONLinesFileReader` | JSONL |
| `MarkItDownFileReader` | PDF, DOCX, HTML через библиотеку markitdown |
| `ParquetFileReader` | Apache Parquet через pyarrow |

### InputReaderFactory

Factory pattern для создания форматного ридера по `InputType` enum.

---

## 4. graphrag-storage — Бэкенды Хранения

**Путь:** `packages/graphrag-storage/graphrag_storage/`

### Storage — ABC асинхронного key-value хранилища

`storage.py:13-135`:
- `get()`, `set()`, `has()`, `delete()`, `clear()`, `keys()`
- `find(pattern)` — поиск по glob-паттерну
- `child(prefix)` — иерархическое именование (namespacing)

### StorageFactory — 4 бэкенда

`storage_factory.py:16-78`:

| Бэкенд | Описание |
|---|---|
| `FileStorage` | Файловая система, async I/O через aiofiles |
| `MemoryStorage` | In-memory dict (для тестов) |
| `AzureBlobStorage` | Azure Blob Storage |
| `AzureCosmosStorage` | Azure Cosmos DB |

### Табличные провайдеры

`tables/` — DataFrame-уровень хранения для промежуточных результатов пайплайна:

- `TableProvider` ABC: `read_dataframe()`, `write_dataframe()`, `list()`, `open()`
- `ParquetTableProvider` — Apache Parquet через pandas
- `CSVTableProvider` — CSV через pandas
- `Table` — обёртка над TableProvider с поддержкой stream write

---

## 5. graphrag-cache — Кэш Пайплайна

**Путь:** `packages/graphrag-cache/graphrag_cache/`

### Cache — ABC асинхронного кэша

`cache.py:15-74`: `get()`, `set()`, `has()`, `delete()`, `clear()`, `child()` — иерархические суб-кэши.

### Реализации

`cache_factory.py:17-89`:

| Кэш | Поведение |
|---|---|
| `JsonCache` | Персистентный, JSON в Storage бэкенде |
| `MemoryCache` | In-memory dict с asyncio locks (потобезопасность) |
| `NoopCache` | Пропускной — всегда miss, никогда не хранит |

### CacheKeyCreator

`key_creator.py:14-30`: Настраиваемая хэш-функция для генерации ключей кэша.

---

## 6. graphrag-llm — Абстракции LLM

**Путь:** `packages/graphrag-llm/graphrag_llm/`

### LLMCompletion — ABC коммитментов

`completion.py:34-265`:
- `create_response()`, `create_streaming_response()`, `create_embedding()`
- **Thread pool** — `completion.py:164-253`: `completion_thread_pool()` создаёт thread pool для параллельных LLM вызовов
- `completion_batch()` — `completion.py:206`: Пакетная обработка с backpressure через queue limiting

### LLMEmbedding — ABC эмбеддингов

`embedding.py:29-191`: Parallel embedding с thread pool для пакетной генерации.

### LiteLLMCompletion — Реализация через litellm

`lite_llm_completion.py:45-303`:
1. Оборачивает `litellm.completion()` / `litellm.acompletion()` (lines 265, 291)
2. Azure Managed Identity auth через `DefaultAzureCredential` (lines 247-249)
3. Mock ответы для тестирования (lines 259-260)
4. Structured JSON output через `response_format_json_object` (lines 262-263)
5. Streaming через async iterator (lines 271-275)

### Middleware Pipeline — Стекер Middleware

`middleware/with_middleware_pipeline.py:30-154`:

Стек обёрток вокруг LLM вызовов (от внешней к внутренней):

1. `with_errors_for_testing` — инжект тестовых сбоев по `failure_rate_for_testing`
2. `with_metrics` — токены и latency метрики
3. `with_rate_limiting` — token-bucket или sliding-window rate limiting
4. `with_retries` — exponential backoff retry
5. `with_cache` — cache lookup до вызова, cache store после ответа
6. `with_request_count` — трекинг count запросов
7. `with_logging` — логирование request/response

### Model Cost Registry

`model_cost_registry/` — Трекинг стоимости токенов на модель для budget tracking.

---

## 7. graphrag-vectors — Векторные Хранилища

**Путь:** `packages/graphrag-vectors/graphrag_vectors/`

### VectorStore — ABC векторного хранилища

`vector_store.py:56-216`:
- `connect()`, `create_index()`, `load_documents()`, `insert()`
- `similarity_search_by_vector()` — ANN search с фильтрацией (lines 136-174)
- `similarity_search_by_text()` — text→vector затем ANN search (lines 176-195)
- `search_by_id()`, `count()`, `remove()`, `update()`

**Timestamp Exploding** — `vector_store.py:97-121`: Авто-эксплод ISO 8601 timestamp в компонента (year, month, day, hour) для range queries.

### Filter Expression DSL — Composable Filter System

`filtering.py:42-386`:

| Класс | Описание |
|---|---|
| `Condition` (lines 59-158) | Сравнение поля: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `contains`, `startswith`, `endswith`, `in_`, `not_in`, `exists` |
| `AndExpr` (lines 161-193) | Логическое И |
| `OrExpr` (lines 195-228) | Логическое ИЛИ |
| `NotExpr` (lines 229-258) | Логическое НЕ |
| `F` builder (lines 277-353) | Fluent API |

Каждое выражение: `evaluate(obj)` для Python-side evaluation + компиляция в native query syntax.

### LanceDBVectorStore — Реализация через LanceDB

`lancedb.py:27-272`:
- IVF_FLAT индекс на vector column (line 75)
- `_compile_filter()` — `lancedb.py:130-185`: Компиляция Pydantic фильтров в LanceDB SQL WHERE
- Similarity search с distance scoring: `score = 1 - abs(float(doc["_distance"]))` (line 215)
- Batch load через PyArrow tables (lines 81-118)

### Другие бэкенды

- `AzureAISearchVectorStore` — Azure AI Search
- `CosmosDBVectorStore` — Azure Cosmos DB

---

## 8. graphrag — Основной Пакет (Indexing + Querying)

**Путь:** `packages/graphrag/graphrag/`

### 8a. Configuration

**GraphRagConfig** — `config/models/graph_rag_config.py:40-333`: Pydantic модель с 20+ полями:

- `completion_models`, `embedding_models` — dict model configs
- `input_storage`, `output_storage`, `update_output_storage` — StorageConfig
- `cache` — CacheConfig
- `chunking` — ChunkingConfig (size, overlap, type)
- `input` — InputConfig
- `table_provider` — Parquet или CSV
- `vector_store` — VectorStoreConfig
- `extract_graph` — ExtractGraphConfig (entity types, max gleanings)
- `extract_graph_nlp` — ExtractGraphNLPConfig
- `summarize_descriptions` — DescriptionSummarizationConfig
- `cluster_graph` — ClusterGraphConfig (max cluster size)
- `extract_claims` — ExtractClaimsConfig
- `community_reports` — CommunityReportsConfig
- `local_search`, `global_search`, `drift_search`, `basic_search` — Search configs
- `workflows` — кастомные workflow (переопределяют встроенные)

`config/enums.py`: `IndexingMethod`, `SearchMethod`, `AsyncType`, `ReportingType`, `CacheType`, `StorageType`, `VectorStoreType`, `ChunkerType`.

### 8b. Indexing Pipeline Architecture

**PipelineFactory** — `index/workflows/factory.py:17-97`:

Регистры: `workflows: dict[str, WorkflowFunction]`, `pipelines: dict[str, list[str]]`.

| Pipeline | Workflows |
|---|---|
| **Standard** | load_input_documents → create_base_text_units → create_final_documents → **extract_graph** → finalize_graph → extract_covariates → create_communities → create_final_text_units → **create_community_reports** → generate_text_embeddings |
| **Fast** | load_input_documents → create_base_text_units → create_final_documents → **build_noun_graph** → prune_graph → finalize_graph → create_communities → create_final_text_units → **create_community_reports_text** → generate_text_embeddings |
| **StandardUpdate** | Standard + update workflows |
| **FastUpdate** | Fast + update workflows |

**PipelineRunner** — `index/run/run_pipeline.py:30-188`:
1. Создаёт storage, cache, table provider из конфига
2. Для **update runs**: delta storage, бэкап предыдущего вывода, новые документы в delta storage (lines 54-89)
3. Итерация по workflow функциям из пайплайна с `(config, context)` (lines 129-145)
4. Yield `PipelineRunResult` после каждого workflow
5. Профилирование через `WorkflowProfiler`
6. Персист `stats.json` и `context.json` после каждого workflow

### 8c. Indexing Operations — Алгоритмы Индексации

#### GraphExtractor (LLM-based)

`index/operations/extract_graph/graph_extractor.py:38-188`:

1. Отправляет текст + entity types к LLM через extraction prompt (lines 85-96)
2. **Glean loop** — `graph_extractor.py:101-121`: Если `max_gleanings > 0`:
   - `CONTINUE_PROMPT` — запрос дополнительных сущностей
   - `LOOP_PROMPT` — проверка наличия ещё сущностей
   - Stop при "N" или достижении максимума
3. Парсинг LLM output с delimited форматом (`<|>` для полей, `##` для записей) (lines 124-178)
4. Экстракция: entities (title, type, description, source_id) и relationships (source, target, description, weight, source_id)

**Summarize Descriptions** — `index/operations/summarize_descriptions/`:
Группирует дубликаты entity/relationship описаний и отправляет к LLM для суммаризации.

#### build_noun_graph (NLP-based)

`index/operations/build_noun_graph/build_noun_graph.py:23-143`:

1. **Node extraction** (lines 56-96): spaCy/TextBlob noun phrase extraction
2. **Edge construction** (lines 99-143): Co-occurrence graph — noun phrases в одном text unit соединяются
3. **PMI weighting** — `graphs/edge_weights.py:10-62`:

```
pmi(x,y) = p(x,y) * log2(p(x,y) / (p(x) * p(y)))
```

Где `p(x,y) = edge_weight / total_edge_weights` и `p(x) = freq(x) / total_freq`

4. **RRF weighting** — `edge_weights.py:65-101`: Reciprocal Rank Fusion

#### cluster_graph — Иерархический Leiden

`index/operations/cluster_graph.py:20-99`:

1. Нормализация edge direction (undirected: lesser node first), дедупликация (lines 63-67)
2. Фильтр по largest connected component через `stable_lcc()` (line 70)
3. `hierarchical_leiden()` из `graspologic_native` (lines 86-88)
4. Level-by-level community mapping с parent cluster hierarchy (lines 34-47)

**stable_lcc** — `graphs/stable_lcc.py:22-75`:
- Deterministic LCC через union-find
- Нормализация нод (HTML unescape, uppercase, strip)
- Стабилизация edge direction

**connected_components** — `graphs/connected_components.py:9-93`:
Union-find (disjoint set) с path compression:
- `find(x)` с path compression (lines 41-45)
- `union(a, b)` (lines 47-50)
- Components sorted by descending size

**hierarchical_leiden** — `graphs/hierarchical_leiden.py:11-54`:
Обёртка над `graspologic_native.hierarchical_leiden()` с настройками `max_cluster_size`, `random_seed`, `resolution`, `randomness`, `iterations`.

#### ClaimExtractor — Экстракция Claims

`index/operations/extract_covariates/claim_extractor.py:46-193`:
1. Отправляет текст + entity spec + claim description к LLM
2. Glean loop аналогичен graph extraction (lines 139-161)
3. Парсинг в: subject_id, object_id, type, status, start_date, end_date, description, source_text
4. Entity resolution через resolved entity mapping (lines 105-117)

#### CommunityReportsExtractor

`index/operations/summarize_communities/community_reports_extractor.py:52-102`:
1. Community graph context → LLM с JSON response format через Pydantic:
   - `CommunityReportResponse`: title, summary, findings (FindingModel list), rating, rating_explanation
2. Конвертация в текст: `# {title}\n\n{summary}\n\n## {finding.summary}\n\n{finding.explanation}`

#### prune_graph

Удаление low-degree node и edge для снижения noise.

### 8d. Query Engine — Алгоритмы Поиска

**Search Engine Factory** — `query/factory.py:37-275`:
- `get_local_search_engine()` — LocalSearch + LocalSearchMixedContext
- `get_global_search_engine()` — GlobalSearch + GlobalCommunityContext
- `get_drift_search_engine()` — DRIFTSearch + DRIFTSearchContextBuilder
- `get_basic_search_engine()` — BasicSearch + BasicSearchContext

#### GlobalSearch — Map-Reduce

`query/structured_search/global_search/search.py:55-521`:

1. **Map phase** (lines 216-274): Параллельные LLM вызовы на batch community short summaries. Извлечение key points как JSON: `{"points": [{"description": ..., "score": ...}]}`. Semaphore для concurrency control (line 104).
2. **Reduce phase** (lines 306-431): Сбор всех key points, filter score > 0, sort descending, truncate по token budget → LLM для финального ответа со streaming.

#### LocalSearch — Single Context Window

`query/structured_search/local_search/search.py:31-183`:
1. Build context из entities, relationships, covariates, community reports через `LocalSearchMixedContext`
2. Форматирование в system prompt
3. Query + context → LLM с streaming

#### DRIFTSearch — Multi-Hop Iterative

`query/structured_search/drift_search/search.py:37-464`:

1. **Primer** — Initial LLM call: intermediate answers + follow-up queries
2. **State machine** (`state.py`): `QueryState` tracks actions, follow-ups, ranks incomplete actions
3. **Main loop** (lines 239-263): До `n_depth` epoch:
   - Rank incomplete actions
   - Execute top-k через LocalSearch (async parallel)
   - Extract follow-up queries из результатов
   - Add to state
4. **Reduce** (lines 350-410): Комбинация всех intermediate answers в единый ответ

#### BasicSearch — Vector RAG

`query/structured_search/basic_search/search.py:32-182`:
1. Embed query → vector similarity search на text units
2. Formatting matching chunks как context
3. Query + context → LLM

#### Context Builders — Алгоритмы Контекста

**local_context.py:30-357**:

- `build_entity_context()` — Entity table с rank, attributes; `max_context_tokens` limit
- `build_covariates_context()` — Covariate table форматирование
- `build_relationship_context()` — Relationship table с приоритизацией:
  1. In-network (edges между выбранными entities)
  2. Out-network по shared connections count (lines 257-294)
  3. Budget: `top_k_relationships * len(selected_entities)`

**GlobalCommunityContext** (`structured_search/global_search/community_context.py`):
Context из community reports + dynamic community selection (LLM scoring relevance к query).

**dynamic_community_selection.py**:
LLM scoring community relevance к query → top communities для map phase.

### 8e. Data Models

`data_model/`:

| Модель | Поля |
|---|---|
| **Entity** (`entity.py:12-69`) | type, description, embeddings, community_ids, text_unit_ids, rank, attributes |
| **Relationship** (`relationship.py`) | source, target, weight, description, attributes |
| **Community** (`community.py`) | community_id, title, summary, rank |
| **CommunityReport** (`community_report.py`) | title, summary, rank, rating, findings |
| **Covariate** (`covariate.py`) | subject_id, object_id, type, description, attributes |
| **TextUnit** (`text_unit.py`) | id, text, entities, relationships, covariates, text_unit_embedding |
| **Document** (`document.py`) | id, name, type, text, chunks |
| **DFS traversal** (`dfs.py`) | Depth-first search для community hierarchy traversal |

### 8f. Prompts

`prompts/index/`: Entity extraction, claim extraction, community reports, description summarization.
`prompts/query/`: Global search (map/reduce), local search, drift search, basic search.

Все через Python `.format()` templating, настраиваемые через `prompt-tune` CLI.

---

## Архитектурные Паттерны

| Паттерн | Применение |
|---|---|
| **Factory** | Каждый подсистема: Factory[T] из graphrag-common для pluggable implementations |
| **Pipeline/DAG** | Workflows — ordered tuples, shared state через `PipelineRunContext` |
| **Middleware Pipeline** | LLM calls в стеке: cache→retry→rate-limit→metrics |
| **Registry** | Workflow functions registered by name, selected by pipeline config |
| **Strategy** | Storage, cache, chunking, input reading, vector stores — switchable via config enum |
| **Template Engine** | Prompts через `.format()`, tune через `prompt-tune` CLI |
| **Async-First** | Pipeline, storage, cache, LLM, input reading — все async |

---

## Диаграмма Архитектуры

```
                    ┌─────────────────────────┐
                    │   CLI (Typer)           │
                    │  init / index / query   │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │  GraphRagConfig         │
                    │  (Pydantic, 20+ fields) │
                    └───────────┬─────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────▼──────┐      ┌────────▼────────┐      ┌───────▼──────┐
│  INDEXING    │      │  PIPELINE       │      │  QUERYING    │
│              │      │  ORCHESTRATION  │      │              │
│ Chunking     │      │  PipelineFactory│      │ GlobalSearch │
│ - Sentence   │      │ - Standard      │      │ (Map-Reduce) │
│ - Token      │      │ - Fast (NLP)    │      │ LocalSearch  │
│              │      │ - Update        │      │ (Mixed ctx)  │
│ Graph Extract│      └────────┬────────┘      │ DRIFTSearch │
│ - LLM (prompt│               │               │ (Multi-hop) │
│   + glean)   │      ┌────────▼────────┐      │ BasicSearch  │
│ - NLP (spaCy│      │  WORKFLOWS      │      │ (Vector RAG) │
│   + PMI)     │      │  (24 workflows) │      └──────────────┘
│              │      └────────┬────────┘
│ Community    │               │
│ Reports (LLM)│      ┌────────▼────────┐
│              │      │  OPERATIONS     │
│ Claims (LLM) │      │  (14 ops)       │
│              │      │  - extract_graph│
│ Clustering   │      │  - cluster_graph│
│ - Leiden     │      │  - summarize_*  │
│ - Union-Find │      │  - extract_*    │
│   (LCC)      │      │  - build_noun_  │
│              │      │    graph        │
│ Edge Weights │      │  - finalize_*   │
│ - PMI        │      │  - prune_graph  │
│ - RRF        │      └────────┬────────┘
└──────────────┘               │
                    ┌──────────▼──────────┐
                    │  INFRASTRUCTURE     │
                    │  Packages           │
                    ├─────────────────────┤
                    │ graphrag-llm        │
                    │  - LiteLLMCompletion│
                    │  - Middleware stack │
                    │    (cache→retry→    │
                    │     rate-limit→     │
                    │     metrics)        │
                    │  - Embedding ABC    │
                    │  - Thread pools     │
                    ├─────────────────────┤
                    │ graphrag-storage    │
                    │  - File/Memory/     │
                    │    AzureBlob/       │
                    │    AzureCosmos      │
                    │  - ParquetTable     │
                    ├─────────────────────┤
                    │ graphrag-cache      │
                    │  - Json/Memory/     │
                    │    Noop             │
                    ├─────────────────────┤
                    │ graphrag-vectors    │
                    │  - LanceDB/         │
                    │    AzureAISearch/   │
                    │    CosmosDB         │
                    │  - Filter DSL       │
                    │    (Pydantic)       │
                    ├─────────────────────┤
                    │ graphrag-chunking   │
                    │ graphrag-input      │
                    │ graphrag-common     │
                    └─────────────────────┘
```

---

*Отчёт сгенерирован на основе анализа исходного кода всех 8 пакетов монорепозитория.*
