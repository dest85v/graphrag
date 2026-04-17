# Packages — TODOs

## P0 — Переход RegexENNounPhraseExtractor с textblob на spaCy

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

## P1 — Добавить поддержку Qdrant как 4-й векторной БД

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

## P2 — Заменить LiteLLM на OpenAI SDK

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

## P3 — Добавить HuggingFace `tokenizers` для не-OpenAI моделей

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
