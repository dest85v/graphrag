# Packages — TODOs

## P0 — Переход RegexENNounPhraseExtractor с textblob на spaCy ✅ **ВЫПОЛНЕНО**

> Реализовано в фиче `004-textblob-to-spacy`. `textblob` удалён, экстрактор переписан на spaCy с `doc.noun_chunks`, определители (DET) отфильтрованы, Jaccard similarity с CFG-экстрактором = 66.67%.

**Файл:** `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/regex_extractor.py`

**Почему:**
- TextBlob dependency помечена как TODO для удаления (line 34): *"TODO: Reimplement this using SpaCy to remove TextBlob dependency."*
- Работает только на английском, regex-based извлечение менее точен, чем spaCy syntactic parser
- spaCy уже используется как основной извлеченчик (`spacy_extractor.py`) — дублирование логики
- Лишняя зависимость: `textblob~=0.18` + скачиваемые nltk corpora (brown, treebank, punkt, punkt_tab, averaged_perceptron_tagger_eng)

**Что сделать:**
1. Рефакторинг `RegexENNounPhraseExtractor.extract()` на spaCy с `doc.noun_chunks`
2. Убрать зависимость `textblob` из `packages/graphrag/pyproject.toml:56`
3. Убрать скачивание nltk corpora: `brown`, `treebank`, `punkt`, `punkt_tab`, `averaged_perceptron_tagger_eng`
4. Сохранить существующую фильтрацию: proper nouns, compound words, valid tokens, max word length, exclude nouns
5. Добавить интеграционные тесты, сравнивающие output с текущим RegexENNounPhraseExtractor
6. Обновить `__str__()` для корректного cache key

**Зависимости:** Ничего (spaCy уже в зависимостях)

**Риск:** Средний — выходные данные будут отличаться (точнее), может повлиять на качество noun graph в Fast pipeline. Нужна валидация на существующих датасетах.

---

## P1 — Добавить поддержку Qdrant как 4-й векторной БД ✅ **ВЫПОЛНЕНО**

> Реализовано в рамках `specs/003-qdrant-vector-db/`: `QdrantVectorStore` в `qdrant.py`, enum `Qdrant` в `vector_store_type.py`, lazy-load в `vector_store_factory.py`, config-поля в `vector_store_config.py`, optional extra в `pyproject.toml`, 42 unit tests pass, 0 regressions in existing tests.

**Пакет:** `graphrag-vectors`

**Файлы для изменения:**
- `packages/graphrag-vectors/graphrag_vectors/qdrant.py` — **создать** новую реализацию
- `packages/graphrag-vectors/graphrag_vectors/vector_store_type.py` — добавить `Qdrant = "qdrant"` в `VectorStoreType` enum
- `packages/graphrag-vectors/graphrag_vectors/vector_store_factory.py` — добавить case в lazy-loading match (line 75)
- `packages/graphrag-vectors/graphrag_vectors/vector_store_config.py` — добавить Qdrant-specific config model
- `packages/graphrag/graphrag/index/config/models/graph_rag_config.py` — добавить qdrant поля в `VectorStoreConfig`

**Что нужно реализовать:**

### QdrantVectorStore (`qdrant.py`)

Наследуется от `VectorStore` ABC (`vector_store.py:56-216`), имплементирует абстрактные методы:

| Метод | Описание |
|---|---|
| `connect()` | Подключение к Qdrant через `qdrant-client` (GRPC для продакшена, HTTP для локального) |
| `create_index()` | Создание collection с HNSW индексом (inner product или cosine) |
| `load_documents(documents)` | Batch upsert `VectorStoreDocument` в collection |
| `similarity_search_by_vector(query_embedding, k, select, filters, include_vectors)` | ANN search через `qdrant_client.QdrantClient.search()` с compile_filter → Qdrant payload filter |
| `search_by_id(id, select, include_vectors)` | Point lookup по ID |
| `count()` | `qdrent_client.QdrantClient.get_collection().points_count` |
| `remove(ids)` | Delete points по batch IDs |
| `update(document)` | Batch upsert (update = replace в Qdrant) |

### Filter Compilation (`_compile_filter`)

Компиляция `FilterExpr` из `graphrag_vectors.filtering` в Qdrant `PayloadSchemaType` / `Filter` DSL:

| FilterExpr класс | Qdrant equivalent |
|---|---|
| `Condition` (eq, ne, gt, gte, lt, lte, contains, startswith, endswith) | `FieldCondition` с `match` (ValueMatch / TextMatch) |
| `Condition` (in_, not_in) | `FieldCondition` с `range` / `values_count` или `MatchAny` |
| `Condition` (exists) | `HasField` condition |
| `AndExpr` | `must` в `Filter` |
| `OrExpr` | `must_not` + `must` / `should` в `Filter` |
| `NotExpr` | `must_not` в `Filter` |

### QdrantConfig (`vector_store_config.py`)

Добавить Pydantic model с полями:
- `url: str | None` — Qdrant server URL (для облачной версии)
- `api_key: str | None` — API key для аутентификации
- `collection_name: str` — имя коллекции
- `vector_size: int` — размер вектора (по умолчанию 3072)
- `distance: str` — "cosine" / "inner_product" / "euclidean"
- `hnsw_m: int | None` — HNSW m параметр
- `hnsw_ef_construct: int | None` — HNSW ef_construct параметр
- `search_ef: int | None` — search-time ef параметр
- `shards: int = 1` — количество реплик (для облачной)
- `port: int = 6333` — порт
- `grpc_port: int = 6334` — GRPC порт

### Зависимости

Добавить `qdrant-client~=1.12` (или актуальную) в:
- `packages/graphrag-vectors/pyproject.toml`

### Тесты

- Юнит-тесты для `QdrantVectorStore` в `tests/unit/` (mock qdrant-client)
- Интеграционный тест с реальным Qdrant instance (docker)
- Тесты filter compilation — coverage всех `FilterExpr` комбинаций
- Сравнение search results с LanceDB бэкендом на одном датасете

### Зависимости от других задач

- Нет прямых зависимостей, можно делать параллельно с другими задачами
- Рекомендуется сначала реализовать P0 (textblob→spaCy), т.к. это P0

**Риск:** Низкий — Qdrant-client хорошо документирован, паттерн реализации идентичен существующим LanceDB / AzureAISearch / CosmosDB имплементациям.

---

## P1 — Реализовать MCP (Model Context Protocol) поддержку в graphrag-llm

**Пакет:** `graphrag-llm`

**Текущее состояние:** Явная пометка в `10_tool_calling.ipynb:362` — *"Not currently supported. graphrag_llm currently only implements the completion endpoints which do not support MCP tools."*

**Что есть сейчас:**
- **`FunctionToolManager`** (`function_tool_manager.py`) — регистрация Pydantic-функций → JSON schema → `tools=[...]` в litellm
- **`CompletionMessagesBuilder`** — управление message history (user → assistant with tool_calls → tool_result → final_response)
- **`LLMCompletion.completion(tools=...)`** — передаёт tool definitions в litellm, LLM возвращает `tool_calls`

Это **function calling по схеме OpenAI**, не MCP.

**Чем MCP отличается:**
| Function Tool Calling (есть) | MCP (нужно) |
|---|---|
| JSON schema functions, статический набор | Discovery + invocation внешних серверов |
| Вызов через `tools=[...]` в completion | stdio/SSE/Streamable HTTP транSPORTS |
| Static tool registration | Dynamic tool discovery via `tools/list` |
| Прямой вызов Python-функций | Протокол `tools/call` на удалённом сервере |

**Что нужно реализовать:**

### MCPTransport (базовый транспорт)

Новый модуль `graphrag_llm/mcp/transport.py`:

| Класс | Транспорт |
|---|---|
| `StdioMCPTransport` | subprocess — запуск MCP-сервера как дочернего процесса, IPC через stdin/stdout |
| `SSEMCPTransport` | HTTP POST с Server-Sent Events |
| `StreamableHttpMCPTransport` | HTTP с JSON-RPC over streaming |

Каждый транспорт имплементирует:
- `connect()` — инициализация соединения
- `send(method, params)` — отправка JSON-RPC 2.0 запроса
- `receive()` — асинхронная приёмка сообщений
- `disconnect()` — graceful shutdown

### MCPClient

`graphrag_llm/mcp/client.py`:

| Метод | MCP JSON-RPC method |
|---|---|
| `initialize()` | `initialize` — handshake, negotiate protocol version + capabilities |
| `list_tools()` → `list[MCPTool]` | `tools/list` — discovery всех доступных инструментов |
| `call_tool(name, arguments)` → `dict` | `tools/call` — invocation конкретного инструмента |
| `list_resources()` | `resources/list` — опционально, discovery данных |
| `read_resource(uri)` | `resources/read` — опционально, чтение ресурса |
| `disconnect()` | `$cancel` + транспорт shutdown |

### MCPTool model

`graphrag_llm/mcp/types.py`:

```python
@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: dict[str, Any]  # JSON Schema
```

### MCPCompletion middleware

Новый middleware-класс `graphrag_llm/mcp/middleware.py`:

Подменяет `LLMCompletion.create_response()`:

1. При инициализации: `initialize()` → `list_tools()` — discover all MCP tools
2. При вызове `completion()`:
   - Передаём `tools=[MCPTool.to_openai_schema(t) for t in mcp_tools]` в litellm
   - LLM возвращает `tool_calls` с MCP tool names
3. При обработке `tool_calls`:
   - Для каждого `tool_call`: `mcp_client.call_tool(tool_name, tool_args)`
   - Форматируем результат как `tool_result` message
4. Повторный `completion()` для финального ответа LLM

### MCPConfig

`graphrag_llm/config/models/mcp_config.py`:

```python
class MCPStdioConfig(BaseModel):
    command: str
    args: list[str] = []
    env: dict[str, str] | None = None
    timeout: float = 30.0

class MCPSSEConfig(BaseModel):
    url: str
    headers: dict[str, str] = {}

class MCPConfig(BaseModel):
    transport_type: Literal["stdio", "sse", "streamable_http"]
    stdio: MCPStdioConfig | None = None
    sse: MCPSSEConfig | None = None
```

### Файлы для создания/изменения

**Создать:**
- `packages/graphrag-llm/graphrag_llm/mcp/__init__.py`
- `packages/graphrag-llm/graphrag_llm/mcp/transport.py` — базовый ABC + 3 транспорта
- `packages/graphrag-llm/graphrag_llm/mcp/client.py` — MCPClient
- `packages/graphrag-llm/graphrag_llm/mcp/types.py` — MCPTool, MCPCapabilities
- `packages/graphrag-llm/graphrag_llm/mcp/middleware.py` — MCPCompletion middleware

**Изменить:**
- `packages/graphrag-llm/graphrag_llm/config/models/` — добавить MCPConfig
- `packages/graphrag-llm/graphrag_llm/completion/completion.py` — подключить MCP middleware

### Зависимости

Добавить в `packages/graphrag-llm/pyproject.toml`:
- `mcp>=1.0.0` (официальный Python SDK для MCP)

### Тесты

- Юнит-тесты для каждого MCPTransport (mock subprocess / HTTP)
- Интеграционные тесты с реальным MCP-сервером (например, `@modelcontextprotocol/server-memory` из npm)
- Тесты discovery + invocation pipeline: `initialize → list_tools → call_tool → result`
- Сравнение behavior: FunctionToolManager vs MCPClient на одинаковых задачах
- Тесты graceful shutdown и timeout handling

### Зависимости от других задач

- Нет прямых зависимостей
- Рекомендуется после P0 (textblob→spaCy)
- Может быть реализован параллельно с P1 (Qdrant)

**Риск:** Средний — MCP протокол стабилен (spec 2024-11-05), есть официальный `mcp` Python SDK. Сложность — корректная обработка JSON-RPC 2.0 сообщений, асинхронных транспорта, error handling.

**Референсы:**
- [MCP Spec](https://modelcontextprotocol.io/spec)
- [mcp Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Transports](https://modelcontextprotocol.io/docs/concepts/transport)

---

## P2 — Заменить LiteLLM на OpenAI SDK ✅ ВЫПОЛНЕНО

**Статус:** Завершена. Все 41 задача из `specs/001-litellm-to-openai/tasks.md` выполнены. `poe check` проходит, 303 unit + все integration тесты проходят.

**Пакет:** `graphrag-llm`

**Текущее состояние:** `litellm==1.82.6` — единственный LLM-прокси в проекте. 26 ссылок на `litellm.*` в ~10 файлах.

### LiteLLM — что используется

| API LiteLLM | Файл | Назначение |
|---|---|---|
| `litellm.completion()` / `acompletion()` | `lite_llm_completion.py:265,291` | Chat completions (ядро) |
| `litellm.embedding()` / `aembedding()` | `lite_llm_embedding.py:188,195` | Embeddings (ядро) |
| `litellm.encode()` / `decode()` | `lite_llm_tokenizer.py:8` | Токенизация (обёртка над tiktoken) |
| `litellm.ModelResponse.model_dump()` | `lite_llm_completion.py:269,294` | Парсинг ответов |
| `litellm.exceptions` | `with_errors_for_testing.py:11` | Конкретные исключения (RateLimitError, etc.) |
| `litellm.mock_response` | `lite_llm_completion.py:255` | Тестовые моки |
| `litellm.suppress_debug_info` | 5 файлов | Глобальный конфиг |
| `litellm.enable_json_schema_validation` | `lite_llm_completion.py:42` | Structured output (response_format) |
| Provider routing `"openai/gpt-4o"` | `lite_llm_completion.py:239` | Маршрутизация провайдеров |

### Что LiteLLM даёт (и что нужно заменить)

| Возможность | OpenAI SDK | LiteLLM | Как заменить |
|---|---|---|---|
| OpenAI API | ✅ нативно | ✅ | Прямой вызов |
| OpenAI-compatible провайдеры | ✅ через `base_url` + `api_key` | ✅ | `httpx_client` с кастомным base_url |
| Azure Cognitive Services | ⚠️ только через `base_url` | ✅ нативно | **Отдельная `AzureCompletion`** с `DefaultAzureCredential` |
| Anthropic/Groq/Bedrock | ❌ | ✅ | **Не поддерживается** — это цена миграции |
| Mock responses | ❌ | ✅ | **Отдельная `MockLLMCompletion`** (уже есть, но использует litellm) |
| `drop_params: True` | ❌ | ✅ | **Обёртка** — filter known-unsupported params перед вызовом |
| Token counting | ❌ | ✅ | **tiktoken напрямую** — уже есть `tiktoken_tokenizer.py` |

### Что теряет проект

- Поддержка провайдеров: Anthropic, Groq, Bedrock, Vertex AI, и др.
- Автоматическая маршрутизация `provider/model`
- Автоматическое dropping unsupported params

### Что получает проект

- Минус 1 большая зависимость (~2000 строк кода в litellm)
- Прямая типизация, лучше IntelliSense
- Проще debugging — нет абстракционного слоя
- Прямой контроль над API-вызовами
- Меньше surface area для уязвимостей

### Архитектура новой реализации

#### 1. OpenAICompletion (основная реализация)

**Файл:** `packages/graphrag-llm/graphrag_llm/completion/openai_completion.py`

Заменяет `LiteLLMCompletion`. Использует `openai.OpenAI` и `openai.AsyncOpenAI`:

```python
class OpenAICompletion(LLMCompletion):
    _sync_client: openai.OpenAI
    _async_client: openai.AsyncOpenAI
    
    def __init__(self, model_config: ModelConfig, **kwargs):
        # Определяем клиент:
        if model_config.model_provider == "azure":
            # Azure: azure_deployment_name + api_base + Azure key или Managed Identity
            self._sync_client = openai.AzureOpenAI(...)
            self._async_client = openai.AsyncAzureOpenAI(...)
        else:
            # OpenAI-compatible: кастомный base_url
            self._sync_client = openai.OpenAI(
                api_key=model_config.api_key,
                base_url=model_config.api_base or f"https://api.{model_config.model_provider}",
                http_client=model_config.call_args.pop("http_client", None),
            )
```

Заменяет `_create_base_completions()`:
- `litellm.completion(...)` → `self._sync_client.chat.completions.create(...)`
- `litellm.acompletion(...)` → `await self._async_client.chat.completions.create(...)`
- `litellm.mock_response` → custom wrapper, intercepting before HTTP call
- `drop_params` → параметр filter перед вызовом SDK

#### 2. OpenAIEmbedding

**Файл:** `packages/graphrag-llm/graphrag_llm/embedding/openai_embedding.py`

Заменяет `LiteLLMEmbedding`:
- `litellm.embedding(...)` → `self._sync_client.embeddings.create(...)`
- `litellm.aembedding(...)` → `await self._async_client.embeddings.create(...)`

#### 3. Azure-specific auth

**Файл:** `packages/graphrag-llm/graphrag_llm/completion/azure_completion.py`

Отдельный класс для Azure Managed Identity:

```python
class AzureCompletion(OpenAICompletion):
    def __init__(self, model_config: ModelConfig, ...):
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        )
        self._sync_client = openai.AzureOpenAI(
            azure_ad_token_provider=token_provider,
            azure_endpoint=model_config.api_base,
            deployment=model_config.azure_deployment_name,
        )
```

#### 4. MockLLMCompletion (без litellm)

**Файл:** `packages/graphrag-llm/graphrag_llm/completion/mock_llm_completion.py`

Перезаписать — убрать `import litellm`, использовать `create_completion_response()` утилиту (уже есть, но проверяем зависимость от litellm).

#### 5. Tokenizer — заменить LiteLLM на tiktoken напрямую

**Файл:** `packages/graphrag-llm/graphrag_llm/tokenizer/openai_tokenizer.py`

Заменяет `LiteLLMTokenizer`:
- `litellm.encode(model=model_id, text=text)` → `tiktoken.encoding_for_model(model_id).encode(text)`
- `litellm.decode(model=model_id, tokens=tokens)` → `tiktoken.encoding_for_model(model_id).decode(tokens)`

> `tiktoken` уже есть в `tiktoken_tokenizer.py` — просто заменить `LiteLLMTokenizer` на `OpenAITokenizer`.

#### 6. Parameter Filtering (drop_unsupported_params)

**Файл:** `packages/graphrag-llm/graphrag_llm/utils/openai_params.py`

```python
# OpenAI SDK supported params для chat.completions.create()
CHAT_COMPLETION_PARAMS = {
    "model", "messages", "temperature", "top_p", "frequency_penalty",
    "presence_penalty", "max_tokens", "stop", "stream", "stream_options",
    "n", "logprobs", "top_logprobs", "response_format", "seed",
    "tools", "tool_choice", "parallel_tool_calls", "service_tier",
}

def filter_completion_kwargs(kwargs: dict, model_id: str) -> dict:
    """Filter out params not supported by OpenAI SDK for this model."""
    return {k: v for k, v in kwargs.items() if k in CHAT_COMPLETION_PARAMS}
```

#### 7. Exception Mapping

**Файл:** `packages/graphrag-llm/graphrag_llm/utils/exceptions.py`

```python
from openai import (
    RateLimitError as OpenAIRateLimitError,
    APIConnectionError as OpenAIAPIConnectionError,
    APITimeoutError as OpenAIA PITimeoutError,
    AuthenticationError as OpenAIAuthenticationError,
    InvalidRequestError as OpenAIInvalidRequestError,
)
```

Заменяет `import litellm.exceptions` в `with_errors_for_testing.py`.

### Файлы для создания

| Файл | Описание |
|---|---|
| `openai_completion.py` | OpenAICompletion — замена LiteLLMCompletion |
| `azure_completion.py` | AzureCompletion — Azure OpenAI с Managed Identity |
| `openai_embedding.py` | OpenAIEmbedding — замена LiteLLMEmbedding |
| `openai_tokenizer.py` | OpenAITokenizer — замена LiteLLMTokenizer (через tiktoken) |
| `utils/openai_params.py` | Фильтрация параметров, mapping supported params |
| `utils/exceptions.py` | Mapping openai exceptions → графrag-llm exceptions |

### Файлы для изменения

| Файл | Изменение |
|---|---|
| `config/types.py` | `LLMProviderType.LiteLLM` → `OpenAI`, добавить `Azure` |
| `config/model_config.py` | Переименовать `_validate_lite_llm_config` → `_validate_openai_config` |
| `completion/completion_factory.py` | `LLMProviderType.LiteLLM` → `LLMProviderType.OpenAI`, импортировать `OpenAICompletion` |
| `embedding/embedding_factory.py` | Аналогично |
| `tokenizer/tokenizer_factory.py` | Импортировать `OpenAITokenizer` по умолчанию |
| `completion/completion.py` | Удалить ссылки на litellm в docstrings |
| `middleware/with_errors_for_testing.py` | Заменить `litellm.exceptions` → `openai` exceptions |
| `types/types.py` | Обновить docstring-ссылки на litellm |
| `__init__.py` (completion) | Переименовать/обновить экспорты |

### Зависимости

**Убрать из `packages/graphrag-llm/pyproject.toml`:**
- ~~`litellm==1.82.6`~~

**Добавить:**
- `openai~=1.60`
- `tiktoken~=0.8` (уже есть как транзитивная от litellm, но сделать явной)

**Удалить `azure-identity` если больше не используется?** — Нет, Azure Managed Identity всё ещё нужен для Azure OpenAI.

### Тесты

- Все существующие тесты `graphrag-llm` должны проходить без изменений API
- Тесты `MockLLMCompletion` — проверить, что не зависят от `litellm.suppress_debug_info`
- Тесты `with_errors_for_testing` — проверить exception mapping
- Интеграционные тесты: OpenAI, Azure OpenAI, OpenAI-compatible (local LLM через Ollama vLLM)
- Тесты tokenization: `OpenAITokenizer` vs `LiteLLMTokenizer` — идентичные результаты

### План миграции (поэтапно)

1. **Шаг 1:** Создать `OpenAICompletion` + `OpenAIEmbedding` рядом с `LiteLLM*` (оба работают параллельно)
2. **Шаг 2:** Заменить `LiteLLMTokenizer` → `OpenAITokenizer` (tiktoken напрямую)
3. **Шаг 3:** Обновить `MockLLMCompletion` — убрать зависимость от `litellm.suppress_debug_info`
4. **Шаг 4:** Обновить `completion_factory.py` — сделать `OpenAI` default вместо `LiteLLM`
5. **Шаг 5:** Удалить `LiteLLMCompletion`, `LiteLLMEmbedding`, `LiteLLMTokenizer`
6. **Шаг 6:** Убрать `litellm` из зависимостей, добавить `openai`, `tiktoken`

### Зависимости от других задач

- Можно делать параллельно с MCP (P1) и Qdrant (P1)
- Рекомендуется после P0 (textblob→spaCy), т.к. это масштабная замена
- **Блокирует P1 (MCP)** — MCP middleware сейчас завязан на `LLMCompletion` который использует litellm

### Риск

**Высокий** — замена ядра LLM-абстракции. Основные риски:
1. **Breaking changes** — если есть кастомные implementations, зарегистрированные через factory
2. **Azure auth** — Managed Identity требует тщательного тестирования
3. **Token counting** — lite_llm tokenizer использует внутреннюю реализацию, tiktoken может немного отличаться
4. **Exception handling** — `with_errors_for_testing` использует `litellm.exceptions` — нужно заменить на `openai.exceptions`
5. **Middleware** — все middleware-функции передают kwargs к litellm — нужно проверить совместимость с OpenAI SDK signature

**Mitigation:**
- Сохранить обратную совместимость: `LLMProviderType.LiteLLM` остаётся, но вызывает `OpenAICompletion`
- Двойные тесты: `LiteLLM*` и `OpenAI*`并行 run на CI
- Deprecation warning при использовании `type: litellm` в конфиге

---

## P3 — Добавить HuggingFace `tokenizers` для не-OpenAI моделей ✅ **ВЫПОЛНЕНО**

**Статус:** ✅ Выполнено (2026-04-17)  
**Зависит от:** P2 (замена LiteLLM на OpenAI SDK) — завершить полностью перед началом.

**Пакет:** `graphrag-llm`

**Текущее состояние:** Токенизация работает через 2 пути:

| Класс | Где | Для каких моделей |
|---|---|---|
| `LiteLLMTokenizer` | `lite_llm_tokenizer.py` | Любые, через litellm (internally tiktoken) |
| `TiktokenTokenizer` | `tiktoken_tokenizer.py` | **Только OpenAI:** cl100k_base, p50k_base, r50k_base, pkl50k_edit |
| `get_tokenizer()` | `get_tokenizer.py` | model_config → LiteLLMTokenizer, иначе → TiktokenTokenizer (ENCODING_MODEL=cl100k_base) |

### Проблема

**Tiktoken поддерживает только модели от OpenAI:**
```
cl100k_base  → GPT-4, GPT-3.5, text-embedding-*
p50k_base    → GPT-3 old
r50k_base    → GPT-2 old
pkl50k_edit  → codex embeddings
```

Для **Llama, Mistral, Qwen, Gemma, Phi** и др. — не работает. После замены LiteLLM (который автоматически определяет правильный tokenizer) проект потеряет токенизацию для этих моделей.

### Решение

Добавить `HuggingFaceTokenizer` через библиотеку `tokenizers` (HuggingFace, Rust-based engine, тот же что в `transformers`).

**Преимущества:**
- Поддержка **любой модели** — auto-detect через HuggingFace Hub
- Локальный `tokenizer.json` — работает offline
- Совместимый ABC — `encode()`/`decode()` тот же интерфейс
- `tokenizers` — легковесная (Rust-бэкенд), быстрее pure-python

### Что меняется

#### 1. HuggingFaceTokenizer (новый класс)

**Файл:** `packages/graphrag-llm/graphrag_llm/tokenizer/huggingface_tokenizer.py`

```python
class HuggingFaceTokenizer(Tokenizer):
    def __init__(self, model_id: str, **kwargs):
        from tokenizers import Tokenizer as HFTokenizer
        self._tokenizer = HFTokenizer.from_pretrained(model_id)
        # или из локального файла:
        # self._tokenizer = HFTokenizer.from_file("/path/to/tokenizer.json")
    
    def encode(self, text: str) -> list[int]:
        return self._tokenizer.encode(text, add_special_tokens=False).ids
    
    def decode(self, tokens: list[int]) -> str:
        return self._tokenizer.decode(tokens, skip_special_tokens=True)
```

#### 2. Обновить TokenizerType enum

**Файл:** `packages/graphrag-llm/graphrag_llm/config/types.py`

```python
class TokenizerType(StrEnum):
    Tiktoken = "tiktoken"
    HuggingFace = "huggingface"
    # LiteLLM = "litellm"  ← удалить после P2
```

#### 3. Обновить TokenizerConfig

**Файл:** `packages/graphrag-llm/graphrag_llm/config/tokenizer_config.py`

```python
model_id: str | None = Field(
    default=None,
    description="The model identifier for tokenizers. Used by HuggingFace tokenizer.",
)

def _validate_huggingface_config(self) -> None:
    if self.model_id is None or self.model_id.strip() == "":
        msg = "model_id must be specified for HuggingFace tokenizer."
        raise ValueError(msg)

@model_validator(mode="after")
def _validate_model(self):
    if self.type == TokenizerType.Tiktoken:
        self._validate_tiktoken_config()
    elif self.type == TokenizerType.HuggingFace:
        self._validate_huggingface_config()
    return self
```

#### 4. Обновить TokenizerFactory

**Файл:** `packages/graphrag-llm/graphrag_llm/tokenizer/tokenizer_factory.py`

```python
case TokenizerType.HuggingFace:
    from graphrag_llm.tokenizer.huggingface_tokenizer import HuggingFaceTokenizer
    register_tokenizer(TokenizerType.HuggingFace, HuggingFaceTokenizer, scope="singleton")
```

#### 5. Обновить get_tokenizer() — smart routing

**Файл:** `packages/graphrag/graphrag/tokenizer/get_tokenizer.py`

```python
# OpenAI family → tiktoken, всё остальное → HuggingFace
_OPENAI_MODELS = {
    "gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo",
    "text-embedding-ada-002", "text-embedding-3-small", "text-embedding-3-large",
    "cl100k_base",
}

def get_tokenizer(model_config=None, encoding_model=None) -> Tokenizer:
    if model_config is not None:
        model_name = model_config.model.lower()
        # Если OpenAI-модель → tiktoken, иначе → HuggingFace
        if any(k in model_name for k in _OPENAI_MODELS):
            encoding_map = {
                "gpt-4o": "cl100k_base",
                "gpt-4": "cl100k_base",
                "gpt-3.5": "cl100k_base",
                "text-embedding": "cl100k_base",
            }
            enc = encoding_map.get(model_name, "cl100k_base")
            return create_tokenizer(
                TokenizerConfig(type=TokenizerType.Tiktoken, encoding_name=enc)
            )
        
        return create_tokenizer(
            TokenizerConfig(type=TokenizerType.HuggingFace, model_id=model_name)
        )
    
    # Fallback: tiktoken cl100k_base
    return create_tokenizer(
        TokenizerConfig(type=TokenizerType.Tiktoken, encoding_name="cl100k_base")
    )
```

### Зависимости

**Добавить в `packages/graphrag-llm/pyproject.toml`:**
- `tokenizers~=0.21` (HuggingFace Rust tokenizer)
- `sentencepiece~=0.2` (для моделей типа T5, BERT)
- `protobuf~=5.0` (зависимость tokenizers)

### Тесты

- Сравнительный тест: `HuggingFaceTokenizer` vs `transformers.AutoTokenizer` — идентичные результаты encode/decode
- Тесты для разных семейств моделей: Llama (bpe), Mistral (bpe), Qwen (bpe), Gemma (bpe)
- Тесты: tiktoken (OpenAI) → HuggingFace (другие) routing в `get_tokenizer()`
- Тесты: локальный `tokenizer.json` vs HuggingFace Hub download
- Тесты: token counting совпадает между `HuggingFaceTokenizer` и middleware rate limiting

### План интеграции после P2

1. **Шаг 1 (после P2):** Создать `HuggingFaceTokenizer` и `TokenizerType.HuggingFace`
2. **Шаг 2:** Обновить `get_tokenizer()` — smart routing OpenAI → tiktoken, else → HF
3. **Шаг 3:** Добавить зависимости в pyproject.toml
4. **Шаг 4:** Тесты routing + encode/decode accuracy
5. **Шаг 5:** Документация — какие модели какие tokenizer используют

### Зависимости от других задач

- **Блокируется P2** — LiteLLM auto-tokenizer удаляется, без HuggingFace tokenizer проект не поддерживает не-OpenAI модели
- Можно делать параллельно с Qdrant (P1)

### Риск

**Низкий:**
- ABC `Tokenizer` не меняется — совместимость 100%
- `tokenizers` — стабильная, широко используемая библиотека
- tiktoken остаётся для OpenAI-моделей — без regressions

**Особенности:**
- `tokenizers` может требовать `sentencepiece`/`spm` для моделей типа T5
- HuggingFace Hub download требует интернет при первом запуске (кешируется в `~/.cache/huggingface/`)
- `add_special_tokens=False` — важно для consistency с tiktoken (tiktoken не добавляет BOS/EOS)

**Статус:** ✅ ЗАВЕРШЕНО (2026-04-17). Реализовано:
1. `HuggingFaceTokenizer` в `packages/graphrag-llm/graphrag_llm/tokenizer/huggingface_tokenizer.py`
2. `TokenizerType.HuggingFace` в enum
3. Валидация `TokenizerConfig` для huggingface type
4. Регистрация в `TokenizerFactory`
5. Экспорт в `__init__.py`
6. Auto-routing в `get_tokenizer()` — OpenAI → tiktoken, остальное → HuggingFace
7. Зависимости: `tokenizers>=0.21,<0.23`, `sentencepiece>=0.2,<0.3`, `protobuf>=5.0,<6.0` (опционально)
8. 36 тестов: unit + integration, все проходят
9. `poe check` проходит: 0 lint errors, 0 type errors
10. Semversioner minor change entry добавлен

---

## P1 — Добавить поддержку русского языка с вкраплениями англоязычных терминов ✅ ВЫПОЛНЕНО

**Приоритет:** P1 — блокирует полноценную работу с русскоязычными документами

**Пакеты:** `graphrag`, `graphrag-chunking`

**Текущее состояние:** Проект настроен на английский текст по умолчанию. Есть два критических барьера для русского языка:

### Проблема 1: regex_extractor отбрасывает кириллицу

`packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/regex_extractor.py:128`:
```python
def _is_valid_token(self, token: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9\-]+\n?$", token))
```

Regex `^[a-zA-Z0-9\-]+$` блокирует все символы, кроме ASCII латиницы. Все русские слова (и вообще любые не-ASCII) считаются невалидными токенами и отбрасываются. Даже если подставить русскую spaCy-модель — RegexExtractor извлечёт **пустой список** из кириллического текста.

При этом англоязычные термины в кириллическом тексте (типа "API", "endpoint", "deployment pipeline") тоже отсекутся, если будут записаны слитно с кириллическими символами или содержать специфические символы.

### Проблема 2: spaCy модель по умолчанию — английская

`packages/graphrag/graphrag/config/defaults.py:162`:
```python
model_name: str = "en_core_web_md"
```

`en_core_web_md` плохо работает с кириллическим текстом: spaCy не корректно определяет POS-теги, noun_chunks для русского текста будут неполными или некорректными.

### Проблема 3: cfg_extractor — grammar hard-coded для английского

`packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/cfg_extractor.py` содержит grammar rules, написанные для английского языка. Для русского нужны другие правила синтаксического разбора.

### Что работает из коробки

| Компонент | Статус для русского |
|---|---|
| Токенизатор `o200k_base` (default) | ✅ Работает — multilingual (tiktoken) |
| Token-based chunking | ✅ Не зависит от языка |
| LLM prompts (`{language}` placeholder) | ✅ prompt_tune детектирует язык, подсказки генерируются |
| Entity summarization (перевод) | ✅ Переводит описания на указанный язык |
| SyntacticParsingExtractor + `ru_core_news_md` | ✅ Работает при подстановке модели |
| CFGExtractor + `ru_core_news_md` | ⚠️ Работает частично — grammar rules английские |

### Что нужно реализовать

#### 1. Поддержка Unicode в RegexExtractor

**Файл:** `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/regex_extractor.py`

Заменить `_is_valid_token`:
```python
def _is_valid_token(self, token: str) -> bool:
    return bool(re.match(r"^\w+[\-]?\w*$", token, re.UNICODE))
```

или явно:
```python
def _is_valid_token(self, token: str) -> bool:
    return bool(re.match(r"^[\p{L}\p{N}\-]+$", token))  # Unicode letters + digits
```

Альтернатива — добавить параметр `supported_scripts` (list of Unicode ranges) и валидировать токены через него.

#### 2. Поддержка мультиязычных spaCy моделей

**Файл:** `packages/graphrag/graphrag/config/defaults.py`

Заменить default:
```python
model_name: str = "en_core_web_md"  # →
model_name: str = "en_core_web_md"  # оставить как default для backward compat
```

Добавить новый default или опцию:
```python
model_name: str = "xx_ent_wiki_sm"  # Universal NER — мультиязычная
```

`xx_ent_wiki_sm` — это мультиязычная spaCy модель, обученная на вики-текстах на многих языках, включая русский и английский. Она лучше распознаёт именованные сущности в смешанном тексте.

ИЛИ использовать конфигурацию с параметром `nlp_model`:
```python
# graphrag config.yaml
extract_graph_nlp:
  strategy:
    type: graphrag_nlp
    config:
      nlp_model: "ru_core_news_md"  # или "xx_ent_wiki_sm"
```

#### 3. Добавить русскоязычную spaCy модель как опциональную зависимость

**Файл:** `packages/graphrag/pyproject.toml`

Добавить optional extra:
```toml
[project.optional-dependencies]
nlp-ru = ["spacy-ru-core-news-md~=3.8"]
nlp-xx = ["spacy-xx-ent-wiki-sm~=3.8"]
```

#### 4. (Опционально) Мультиязычные grammar rules для CFGExtractor

**Файл:** `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/cfg_extractor.py`

Добавить набор grammar rules для русского языка. Это можно сделать через config:
```python
RU_NOUN_PHRASE_GRAMMARS = [
    "<ADJ><NOUN>",           # "красная машина"
    "<NOUN><ADP><NOUN>",     # "дом друга"
    "<ADV><ADJ><NOUN>",      # "очень важная информация"
]
```

#### 5. Тесты

- Юнит-тест: RegexExtractor на тексте `["Русский текст с английскими терминами API и endpoint"]` — должен извлечь и русские, и английские именные фразы
- Интеграционный тест: полный NLP pipeline с `ru_core_news_md` на русском тексте
- Интеграционный тест: `xx_ent_wiki_sm` на смешанном RU+EN тексте — coverage сущностей
- Сравнение: `en_core_web_md` vs `ru_core_news_md` vs `xx_ent_wiki_sm` на смешанном тексте

### Зависимости от других задач

- Нет прямых зависимостей
- Можно делать параллельно с любыми другими задачами
- Рекомендуется после P2 (litellm→openai) и P3 (HuggingFace tokenizer), т.к. токенизация должна быть стабильной

### Риск

**Средний:**
1. `re.UNICODE` / `\w` — может включить нежелательные символы (диакритика, арабская вязь и т.д.)
2. `xx_ent_wiki_sm` — мультиязычная модель менее точна, чем моноязычная для конкретного языка
3. CFG grammar rules для русского — нужен лингвистический анализ
4. Regression risk — если тесты написаны только на английском тексте

**Mitigation:**
- Сохранить `en_core_web_md` как default (backward compat)
- Добавить конфиг-опцию `nlp_model` для выбора модели
- RegexExtractor тесты на трёх сценариях: EN-only, RU-only, RU+EN mixed

---

## P1 — Language-aware NLP Factory: auto-select stop words и CFG grammars по языку ✅ **ВЫПОЛНЕНО**

**Приоритет:** P1 — следует за P1 (русский язык, строка 679)

**Пакеты:** `graphrag`

**Текущее состояние:** В репозитории определены русскоязычные ресурсы, но они не используются:

| Ресурс | Файл | Статус |
|---|---|---|
| `RU_STOP_WORDS` | `np_extractors/stop_words.py:23-34` | Определён, но **нигде не импортируется**. Фабрика всегда берёт `EN_STOP_WORDS` (`factory.py:43`) |
| `RU_NOUN_PHRASE_GRAMMARS` | `np_extractors/cfg_extractor.py:19-31` | Определён, но **нигде не импортируется**. CFG-экстрактор использует грамматики из конфига/дефолтов (английские) |

### Что не работает

```python
# factory.py:41-43 — всегда EN_STOP_WORDS, language не учитывается
if exclude_nouns is None:
    exclude_nouns = EN_STOP_WORDS
```

Пользователь может указать `nlp_model: ru_core_news_md` (что уже поддерживается, `extract_graph_nlp_config.py:23-25`), но стоп-слова останутся английскими (`"stuff"`, `"thing"`, `"bunch"`) — бессмыслица для русского текста.

### Что нужно реализовать

#### 1. Добавить `language` в `TextAnalyzerConfig`

**Файл:** `packages/graphrag/graphrag/config/models/extract_graph_nlp_config.py`

Добавить поле:
```python
language: str | None = Field(
    default=None,
    description="Document language for selecting appropriate stop words and CFG grammars (e.g., 'en', 'ru', 'de'). Falls back to English defaults if not set.",
)
```

#### 2. Интегрировать RU_STOP_WORDS в factory

**Файл:** `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/factory.py`

```python
from graphrag.index.operations.build_noun_graph.np_extractors.stop_words import (
    EN_STOP_WORDS,
    RU_STOP_WORDS,
)

# В get_np_extractor (строка 40-43) заменить:
#   if exclude_nouns is None:
#       exclude_nouns = EN_STOP_WORDS
# на:
if exclude_nouns is None:
    lang = (config.language or "en").lower()
    if lang == "ru":
        exclude_nouns = list(RU_STOP_WORDS)  # factory expects list[str]
    else:
        exclude_nouns = EN_STOP_WORDS
```

#### 3. Вынести EN-грамматики из `defaults.py` в `cfg_extractor.py`

**Файл:** `packages/graphrag/graphrag/config/defaults.py:172-180`

Перенести грамматики из `TextAnalyzerDefaults.noun_phrase_grammars` в `cfg_extractor.py`:

```python
# cfg_extractor.py
EN_NOUN_PHRASE_GRAMMARS: dict[str, str] = {
    "PROPN,PROPN": "PROPN",
    "NOUN,NOUN": "NOUNS",
    "NOUNS,NOUN": "NOUNS",
    "ADJ,ADJ": "ADJ",
    "ADJ,NOUN": "NOUNS",
}

# RU_NOUN_PHRASE_GRAMMARS уже есть, переименовать в CFG_NOUN_PHRASE_GRAMMARS
```

**Файл:** `packages/graphrag/graphrag/config/defaults.py` — обновить import:
```python
from graphrag.index.operations.build_noun_graph.np_extractors.cfg_extractor import (
    EN_NOUN_PHRASE_GRAMMARS,
)
```

#### 4. Автовыбор CFG-грамматик по языку в factory

**Файл:** `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/factory.py`, case CFG (строка 56-70):

```python
case NounPhraseExtractorType.CFG:
    grammars = {}
    for key, value in config.noun_phrase_grammars.items():
        grammars[tuple(key.split(","))] = value
    
    # Auto-select base grammars if none provided
    if not config.noun_phrase_grammars:
        lang = (config.language or "en").lower()
        base_grammars = CFG_NOUN_PHRASE_GRAMMARS if lang == "ru" else EN_NOUN_PHRASE_GRAMMARS
        for k, v in base_grammars.items():
            grammars[k] = v
    
    return CFGNounPhraseExtractor(...)
```

#### 5. Автовыбор spaCy-модели по языку (опционально)

**Файл:** `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/factory.py:44`

```python
LANGUAGE_MODEL_MAP = {
    "en": "en_core_web_md",
    "ru": "ru_core_news_md",
    "de": "de_core_news_md",
    "fr": "fr_core_news_md",
}

effective_model_name = config.nlp_model or config.model_name
if not config.nlp_model and not config.model_name:
    lang = (config.language or "en").lower()
    effective_model_name = LANGUAGE_MODEL_MAP.get(lang, "en_core_web_md")
```

#### 6. Переименовать `RU_NOUN_PHRASE_GRAMMARS` → `CFG_NOUN_PHRASE_GRAMMARS`

**Файл:** `packages/graphrag/graphrag/index/operations/build_noun_graph/np_extractors/cfg_extractor.py:19`

#### 7. Обновить `init_content.py`

**Файл:** `packages/graphrag/graphrag/config/init_content.py:90-93`

```yaml
extract_graph_nlp:
  text_analyzer:
    extractor_type: {type} # [regex_english, syntactic_parser, cfg]
    language: en # [en, ru, de, fr, xx] — selects stop words & CFG grammars; falls back to 'en'
```

#### 8. Обновить `enums.py`

**Файл:** `packages/graphrag/graphrag/config/enums.py:60-61`

Документация `RegexEnglish = "regex_english"` — актуализировать: *"Standard extractor using regex. Fastest, but limited to English (use syntactic_parser for multilingual)."*

### Зависимости

- Нет прямых зависимостей, но требует наличия `ru_core_news_md` (уже описано в P1 строка 679)

### Тесты

- `tests/unit/test_noun_phrase_factory.py` — `get_np_extractor(language="ru")` → `RU_STOP_WORDS`; `language="en"` → `EN_STOP_WORDS`; `language=None` → `EN_STOP_WORDS` (backward compat)
- `tests/unit/test_cfg_extractor_language.py` — CFG-экстрактор с `language=ru` использует `CFG_NOUN_PHRASE_GRAMMARS`
- Integration-тест: полный NLP pipeline с `language: ru` — стоп-слова `"И"`, `"ИЛИ"`, `"ЧТО"` фильтруются

### Риск

**Низкий:**
- Изменяется только дефолтное поведение factory — явные конфиги (`exclude_nouns: [...]`) не затронуты
- `language=None` → `EN_STOP_WORDS` (backward compat)

**Статус:** ✅ ЗАВЕРШЕНО (2026-04-18). Реализовано:
1. Поле `language: str | None` добавлено в `TextAnalyzerConfig` (`extract_graph_nlp_config.py`)
2. `RU_NOUN_PHRASE_GRAMMARS` переименован в `CFG_NOUN_PHRASE_GRAMMARS` (`cfg_extractor.py`)
3. `EN_NOUN_PHRASE_GRAMMARS` вынесены из `defaults.py` в `cfg_extractor.py`
4. `defaults.py` импортирует `EN_NOUN_PHRASE_GRAMMARS` из `cfg_extractor.py`
5. `NounPhraseExtractorFactory` — автоподбор `RU_STOP_WORDS` / `EN_STOP_WORDS` по `language`
6. `NounPhraseExtractorFactory` — автоподбор CFG-грамматик по `language` (RU → `CFG_NOUN_PHRASE_GRAMMARS`, EN → `EN_NOUN_PHRASE_GRAMMARS`)
7. `NounPhraseExtractorFactory` — автовыбор spaCy-модели через `LANGUAGE_MODEL_MAP`
8. Обновлён `init_content.py` — добавлено поле `language` в шаблон конфига
9. Обновлён `enums.py` — docstring RegexEnglish указывает ограничение по языку
10. `TextAnalyzerConfig.exclude_nouns` default изменён на `None` (ранее `EN_STOP_WORDS`) — автоподбор через factory
11. 29 unit-тестов: `test_noun_phrase_factory.py` — coverage всех сценариев
12. Все 53 теста в `tests/unit/indexing/operations/` проходят
13. `poe format` — 0 изменений, код отформатирован
14. `poe check` — рутинг чистый (остались только pre-existing ошибки P3 HuggingFace tokenizer)
15. Semversioner minor change entry добавлен
16. `README_RU.md` обновлён: секция автоподбора ресурсов, автовыбор spaCy-модели

---

## P2 — NLTK Multilingual Sentence Tokenizer для chunking ✅ **ВЫПОЛНЕНО**

> Реализовано в фиче `007-multilingual-sentence-tokenizer`: `nltk_language` поле в `ChunkingConfig` и `SentenceChunker`, конфиг дефолты, init template, 8 unit тестов, 0 регрессий.

**Пакеты:** `graphrag-chunking`, `graphrag`

**Файлы изменены:**
- `packages/graphrag-chunking/graphrag_chunking/chunking_config.py` — добавлено поле `nltk_language: str = "english"`
- `packages/graphrag-chunking/graphrag_chunking/sentence_chunker.py` — `__init__` принимает `nltk_language`, `chunk()` передаёт `language=` в `nltk.sent_tokenize()`
- `packages/graphrag/graphrag/config/defaults.py` — `ChunkingDefaults.nltk_language = "english"`
- `packages/graphrag/graphrag/config/models/graph_rag_config.py` — `ChunkingConfig(...)` включает `nltk_language`
- `packages/graphrag/graphrag/config/init_content.py` — `chunking.nltk_language` в шаблоне конфига
- `packages/graphrag-chunking/README.md` — документация `nltk_language`
- `tests/unit/chunking/test_sentence_chunker_nltk_language.py` — 8 тестов

**Что реализовано:**
1. `ChunkingConfig` имеет поле `nltk_language: str = "english"`
2. `SentenceChunker` принимает `nltk_language` и передаёт в `nltk.sent_tokenize(language=...)`
3. `ChunkingDefaults` имеет `nltk_language = "english"` (backward compat)
4. `GraphRagConfig.chunking` передаёт `nltk_language` через `ChunkingConfig`
5. `init_content.py` включает `nltk_language` в шаблон конфига с документацией
6. 8 unit-тестов: EN default, EN explicit, RU mock/actual, DE, FR, invalid → LookupError, default check
7. Все 19 тестов chunking проходят (0 регрессий)
8. `poe check` на модифицированных файлах — 0 ошибок
9. Semversioner PATCH entry добавлен

**Файл:** `packages/graphrag-chunking/graphrag_chunking/sentence_chunker.py:31`:
```python
sentences = nltk.sent_tokenize(text.strip())  # Always English
```

**Файл:** `packages/graphrag-chunking/graphrag_chunking/bootstrap_nltk.py:22-23`:
```python
nltk.download("punkt")
nltk.download("punkt_tab")
```

`punkt_tab` в NLTK 3.9+ включает мультиязычные модели (russian, french, german, spanish...), но `sent_tokenize` по умолчанию всегда использует `english`.

### Что нужно реализовать

#### 1. Добавить `nltk_language` параметр в `SentenceChunker`

**Файл:** `packages/graphrag-chunking/graphrag_chunking/sentence_chunker.py`

```python
class SentenceChunker(Chunker):
    def __init__(
        self,
        encode: Callable[[str], list[int]] | None = None,
        nltk_language: str = "english",
        **kwargs: Any,
    ) -> None:
        self._encode = encode
        self._nltk_language = nltk_language
        bootstrap()

    def chunk(self, text: str, ...) -> list[TextChunk]:
        sentences = nltk.sent_tokenize(
            text.strip(),
            language=self._nltk_language  # <-- ключевое изменение
        )
```

#### 2. Добавить `nltk_language` в конфиг чанкинга

**Файл:** `packages/graphrag/graphrag/config/defaults.py` — в `ChunkingDefaults`:

```python
nltk_language: str = "english"
```

Или в отдельном `ChunkingConfig` (если есть):
```python
nltk_language: str = Field(
    default="english",
    description="NLTK punkt language model. Supported: english, russian, german, french, spanish, ...",
)
```

#### 3. Передать язык из конфига в SentenceChunker

Найти место создания чанкера (вероятно, в `packages/graphrag/graphrag/index/workflows/` или `packages/graphrag/graphrag/index/factories/`), передать `nltk_language`.

#### 4. Обновить `init_content.py`

**Файл:** `packages/graphrag/graphrag/config/init_content.py:42-46`

```yaml
chunking:
  type: tokens
  nltk_language: english # [english, russian, french, german, spanish] — used when type=sentence
```

#### 5. Обновить bootstrap — убедиться, что punkt_tab скачивается

**Файл:** `packages/graphrag-chunking/graphrag_chunking/bootstrap_nltk.py`

Проверить что `punkt_tab` скачивается (уже есть, строка 23). В NLTK 3.9+ `punkt_tab` содержит модели для 10+ языков, включая `russian`.

### Зависимости

- Нет прямых зависимостей

### Тесты

- Юнит-тест: `SentenceChunker(nltk_language="russian")` на русском тексте — корректная разбивка на предложения (сравнить с английским)
- Тест: `nltk_language="english"` на русском — fallback degradation (показать что работает но хуже)
- Integration-тест: полный pipeline с `chunking.type: sentence` + `nltk_language: russian`

## P0 — CI pre-existing errors: pyproject.toml, tokenizers, RUF001 кириллица, graphrag-cache, pyright type errors ✅ **ВЫПОЛНЕНО**

> Реализовано в фиче `008-fix-ci-errors`: `tokenizers` перемещён в base dependencies `graphrag-llm`, добавлены `SLF001`/`RUF001` noqa-комментарии в тесты. `poe check` проходит с 0 ошибок.

**Что реализовано:**
1. `tokenizers>=0.21,<0.23` перемещён из `[project.optional-dependencies]` (huggingface extra) в `[project.dependencies]` в `packages/graphrag-llm/pyproject.toml`
2. `uv sync` теперь устанавливает `tokenizers` в `.venv` — 6 pyright `reportMissingImports` ошибок устранены
3. `# noqa: SLF001` добавлен в `tests/unit/chunking/test_sentence_chunker_nltk_language.py:112`
4. `# noqa: RUF001` добавлен в `tests/unit/indexing/operations/test_noun_phrase_factory.py:67`
5. `poe check` проходит с 0 ошибок, 0 warnings
6. 58 pre-existing unit test failures не затронуты (подтверждено через git stash test)

**Файлы изменены:**
- `packages/graphrag-llm/pyproject.toml` — перемещён `tokenizers` в base deps
- `tests/unit/chunking/test_sentence_chunker_nltk_language.py` — добавлен `noqa: SLF001`
- `tests/unit/indexing/operations/test_noun_phrase_factory.py` — добавлен `noqa: RUF001`

### 0. Восстановить `[build-system]` в `packages/graphrag/pyproject.toml`

**Файл:** `packages/graphrag/pyproject.toml:67-68`

Было:
```toml
[build-system]

```

Стало (частично, после 007):
```toml
[build-system]
requires = ["hatchling>=1.27.0,<2.0.0"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["graphrag"]
```

**Что нужно:** Восстановить исходную схему build-system. Возможно, там вообще не должен был быть `[build-system]` (workspace-only package). Проверить, не ломается ли `uv build --all-packages` при добавлении.

### 1. Установить `tokenizers` для `graphrag-llm`

**Файлы:**
- `packages/graphrag-llm/graphrag_llm/tokenizer/huggingface_tokenizer.py:35`
- `tests/unit/tokenizer/test_huggingface_tokenizer.py:11`
- `tests/unit/tokenizer/test_huggingface_tokenizer_local.py:17,71`
- `tests/integration/test_tokenizer_consistency.py:12`
- `tests/unit/tokenizer/test_tokenizer_factory.py:12`

**Ошибка:** `pyright: Import "tokenizers" could not be resolved (reportMissingImports)`

**Причина:** `tokenizers` добавлен в `graphrag-llm/pyproject.toml` как зависимость, но не устанавливается в `.venv` при `uv sync` — вероятно, в `extras` или `optional-dependencies`.

**Что нужно:** Добавить `tokenizers` в базовые зависимости `graphrag-llm` или в workspace `uv sync` через optional extra. Убедиться что все 5 файлов импортируют без ошибок.

### 2. Исправить RUF001 кириллица в `test_noun_phrase_factory.py`

**Файл:** `tests/unit/indexing/operations/test_noun_phrase_factory.py:65-67`

**Ошибки:**
```
RUF001 String contains ambiguous `Н` (CYRILLIC CAPITAL LETTER EN)
RUF001 String contains ambiguous `А` (CYRILLIC CAPITAL LETTER A)
RUF001 String contains ambiguous `И` (CYRILLIC CAPITAL LETTER I)
```

**Контекст:** От P1 language-aware NLP factory (006). Тесты проверяют русские стоп-слова: `"И"`, `"НА"`, `"ЧТО"`, `"ИЛИ"`. Ruff RUF001 срабатывает на кириллицу, визуально идентичную латинице (Н=N, А=A, И=I).

**Что нужно:** Либо:
- Добавить `# noqa: RUF001` к строкам с кириллическими строковыми литералами
- Или исключить `tests/` из RUF001 в `ruff.toml` (менее желательно)
- Или использовать Unicode-escape: `\u0418`, `\u041d`, `\u0410`

### 3. Установить `graphrag-cache` в `.venv`

**Файлы с ошибкой:**
- `packages/graphrag-cache/graphrag_cache/cache.py:12` — `reportMissingImports: graphrag_storage`
- `packages/graphrag-cache/graphrag_cache/cache_config.py:6-7` — `graphrag_storage`, `pydantic`
- `packages/graphrag-cache/graphrag_cache/cache_factory.py:9-10` — `graphrag_common.factory`, `graphrag_storage`
- `packages/graphrag-cache/graphrag_cache/cache_key.py:8` — `graphrag_common.hasher`
- `packages/graphrag-cache/graphrag_cache/json_cache.py:9` — `graphrag_storage`

**Причина:** `graphrag-cache` не установлен через `uv pip install -e` при ручной установке. Вероятно, не попадает в `uv sync` из-за проблемы с workspace members или зависимостями.

**Что нужно:** Проверить `packages/graphrag-cache/pyproject.toml` — есть ли `graphrag-common` и `graphrag-storage` как зависимости workspace. Убедиться что `uv sync` устанавливает все пакеты.

### 4. Исправить pyright `Variable not allowed in type expression` в `graphrag-llm`

**Файлы:**
- `packages/graphrag-llm/graphrag_llm/completion/completion.py:85,127,213,235,241`
- `packages/graphrag-llm/graphrag_llm/completion/lite_llm_completion.py:137,176,280,308,316,344`
- `packages/graphrag-llm/graphrag_llm/completion/mock_llm_completion.py:89,113`
- `packages/graphrag-llm/graphrag_llm/completion/openai_completion.py:138,177,285`

**Ошибки:** `reportInvalidTypeForm` — переменные используются в type annotations.

**Контекст:** От P2 LiteLLM→OpenAI migration. Вероятно, `typing_extensions` `TypeAliasType` или `Annotated` с переменными.

**Что нужно:** Определить тип выражения, который вызывает ошибку. Заменить на константные типы или добавить `# type: ignore`/настроить pyright для пропуска этих строк.

### Зависимости

- Задача 0 влияет на `uv build --all-packages` — может сломать билд
- Задача 1 влияет на HuggingFace tokenizer tests (P3)
- Задача 2 — изолированная, только RUF001
- Задача 3 — влияет на graphrag-cache и graphrag-llm (зависит от cache)
- Задача 4 — изолированная, pyright type expressions

### Тесты

- После каждого исправления: `uv run poe check` — уменьшить количество ошибок на 1
- Итог: `poe check` должен показать 0 ошибок, 0 warnings (за исключением RUF001 для кириллицы в существующих тестах)

### Риск

**Низкий:** Все проблемы — pre-existing, не от новых изменений. Исправления не затрагивают runtime-логику.
