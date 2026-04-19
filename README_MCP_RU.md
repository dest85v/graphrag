# Использование MCP в graphrag-llm

**Model Context Protocol (MCP)** — стандарт открытого протокола для взаимодействия LLM с внешними инструментами и данными. Данный README описывает, как подключить MCP-серверы к графовому RAG-конвейеру GraphRAG.

## Обзор

MCP-поддержка позволяет LLM-модели автоматически обнаруживать и вызывать внешние инструменты (выполнение команд, чтение файлов, вызовы API и т.д.) во время генерации ответов. Конвейер GraphRAG прозрачно обрабатывает:

1. **Обнаружение инструментов** — клиент подключается к MCP-серверу и получает список доступных инструментов
2. **Вызов инструментов** — LLM решает, какой инструмент использовать; конвейер выполняет вызов через MCP-сервер
3. **Форматирование результатов** — результаты вызова инструментов возвращаются LLM для формирования финального ответа

## Требования

- Python 3.11 — 3.13
- Пакет `graphrag-llm` с поддержкой MCP

## Установка

MCP-SDK является необязательной зависимостью:

```bash
# Вариант 1: установка через extra-зависимость
uv add "graphrag-llm[mcp]>=1.0.0"

# Вариант 2: установка SDK вручную
uv add "mcp>=1.0.0,<2.0.0"
```

## Типы транспорта

Поддерживаются три способа подключения к MCP-серверу:

| Транспорт | Описание | Когда использовать |
|-----------|----------|-------------------|
| **stdio** | Запуск сервера как дочернего процесса, IPC через stdin/stdout | Локальные серверы, скрипты на Python/Node |
| **SSE** | HTTP с Server-Sent Events | Удалённые серверы, legacy-интеграции |
| **Streamable HTTP** | HTTP с потоковым JSON-RPC | Современные MCP-серверы (spec 2025-06-18+) |

## Базовое использование

### Подключение через stdio

```python
import asyncio
from openai import AsyncOpenAI
from graphrag_llm.completion import OpenAICompletionFactory
from graphrag_llm.config import ModelConfig

# 1. Настройка MCP-сервера
mcp_config = {
    "mcp_config": {
        "transport_type": "stdio",
        "stdio": {
            "command": "python",                    # исполняемый файл
            "args": ["-m", "my_mcp_server"],       # аргументы запуска
            "env": None,                             # наследовать env родительского процесса
        },
        "init_timeout": 30.0,    # таймаут инициализации (сек)
        "tool_timeout": 30.0,    # таймаут вызова инструмента (сек)
    }
}

# 2. Создание конфигурации модели с включённым MCP
model_config = ModelConfig(
    model_provider="openai",
    model="gpt-4o",
    api_key="sk-...",
    call_args=mcp_config,
)

# 3. Создание клиента завершений
completion = OpenAICompletionFactory(
    model_id="gpt-4o",
    model_config=model_config,
    # ... остальные параметры (tokenizer, metrics_store и т.д.)
)

# 4. Запрос — MCP-инструменты используются автоматически
response = completion.completion(
    messages=[{"role": "user", "content": "Какие файлы находятся в /tmp?"}],
)

# LLM автоматически:
# - Обнаружит доступные MCP-инструменты от сервера
# - Выберет подходящий инструмент (например, "list_files")
# - Выполнит вызов через MCP-сервер
# - Отправит результат обратно LLM
# - Вернёт финальный ответ
print(response.content)
```

### Подключение через SSE

```python
mcp_config = {
    "mcp_config": {
        "transport_type": "sse",
        "sse": {
            "url": "http://localhost:8080/mcp",
            "headers": {"Authorization": "Bearer token"},  # опциональные заголовки
            "timeout": 5.0,           # таймаут HTTP-запросов (сек)
            "sse_read_timeout": 300.0, # таймаут чтения SSE (сек)
        },
        "init_timeout": 30.0,
        "tool_timeout": 30.0,
    }
}
```

### Подключение через Streamable HTTP

```python
mcp_config = {
    "mcp_config": {
        "transport_type": "streamable_http",
        "streamable_http": {
            "url": "http://localhost:8000/mcp",
            "headers": {"Authorization": "Bearer token"},  # опциональные заголовки
            "timeout": 5.0,  # таймаут HTTP-запросов (сек)
        },
        "init_timeout": 30.0,
        "tool_timeout": 30.0,
    }
}
```

## Примеры MCP-серверов

### Тестовый сервер памяти (npm)

Установите и запустите встроенный MCP-сервер для тестирования:

```bash
npx -y @modelcontextprotocol/server-memory
```

Подключение через stdio:

```python
mcp_config = {
    "mcp_config": {
        "transport_type": "stdio",
        "stdio": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"],
        },
    }
}
```

### Пользовательский сервер на Python

Простой MCP-сервер на Python:

```python
# my_mcp_server.py
import asyncio
import mcp.types as types
from mcp.server import Server

app = Server("my-server")

@app.tool("echo")
async def echo(message: str) -> str:
    """Эхо-инструмент: возвращает введённое сообщение."""
    return f"Эхо: {message}"

@app.tool("calculate")
async def calculate(expression: str) -> str:
    """Вычисляет математическое выражение."""
    result = eval(expression)  # Только для доверенных выражений!
    return str(result)

if __name__ == "__main__":
    asyncio.run(app.run_stdio())
```

### Использование с GraphRAG

```python
mcp_config = {
    "mcp_config": {
        "transport_type": "stdio",
        "stdio": {
            "command": "python",
            "args": ["my_mcp_server.py"],
        },
    }
}

model_config = ModelConfig(
    model_provider="openai",
    model="gpt-4o",
    api_key="sk-...",
    call_args=mcp_config,
)

completion = OpenAICompletionFactory(
    model_id="gpt-4o",
    model_config=model_config,
)

# LLM автоматически использует инструменты echo и calculate
response = completion.completion(
    messages=[{"role": "user", "content": "Скажи эхо: привет мир, а потом вычисли 2+2"}],
)
print(response.content)
```

## Как работает конвейер

```
Пользователь: "Какие файлы в /tmp?"
        │
        ▼
┌───────────────────────────────────────────────┐
│  MCPCompletionMiddleware                     │
│  1. Подключается к MCP-серверу               │
│  2. Обнаруживает доступные инструменты        │
│  3. Передаёт описание инструментов LLM        │
└───────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────┐
│  LLM (GPT-4o)                                │
│  "Нужно вызвать list_files"                  │
│  → tool_call: {name: "list_files",           │
│                 arguments: {path: "/tmp"}}    │
└───────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────┐
│  MCP Client                                   │
│  1. Вызывает MCP-сервер с именем инструмента │
│  2. Получает результат: "file1.txt, file2"   │
│  3. Форматирует как tool_result сообщение     │
└───────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────┐
│  LLM (GPT-4o) — получает результат           │
│  "В /tmp находятся: file1.txt, file2"        │
└───────────────────────────────────────────────┘
```

Цикл может повторяться до 10 раз (безопасный лимит) для сложных запросов, требующих нескольких вызовов инструментов.

## Отключение MCP

MCP полностью отключается простым исключением конфигурации. Система полностью совместима «назад» — без `mcp_config` конвейер работает как стандартный LLM без каких-либо MCP-взаимодействий:

```python
model_config = ModelConfig(
    model_provider="openai",
    model="gpt-4o",
    api_key="sk-...",
    # Без mcp_config — работает без MCP
)
```

## Структура конфигурации

### MCPConfig

| Поле | Тип | Обязательное | Описание |
|------|-----|:---:|----------|
| `transport_type` | `str` | Да | Тип транспорта: `"stdio"`, `"sse"`, `"streamable_http"` |
| `stdio` | `MCPStdioConfig \| None` | Н* | Конфигурация stdio-транспорта |
| `sse` | `MCPSSEConfig \| None` | Н* | Конфигурация SSE-транспорта |
| `streamable_http` | `MCPStreamableHTTPConfig \| None` | Н* | Конфигурация Streamable HTTP |
| `init_timeout` | `float` | Нет | Таймаут инициализации (по умолч. 30.0 сек) |
| `tool_timeout` | `float` | Нет | Таймаут вызова инструмента (по умолч. 30.0 сек) |

\* Обязательно для соответствующего `transport_type`, иначе — ошибка валидации.

### MCPStdioConfig

| Поле | Тип | Обязательное | Описание |
|------|-----|:---:|----------|
| `command` | `str` | Да | Путь к исполняемому файлу (например, `"python"`, `"node"`) |
| `args` | `list[str] \| None` | Нет | Аргументы запуска (по умолч. `[]`) |
| `env` | `dict[str, str] \| None` | Нет | Переменные окружения для subprocess (по умолч. наследуются) |

### MCPSSEConfig

| Поле | Тип | Обязательное | Описание |
|------|-----|:---:|----------|
| `url` | `str` | Да | URL SSE-эндпоинта |
| `headers` | `dict[str, str] \| None` | Нет | Дополнительные HTTP-заголовки |
| `timeout` | `float` | Нет | Таймаут HTTP-запросов (по умолч. 5.0 сек) |
| `sse_read_timeout` | `float` | Нет | Таймаут чтения SSE (по умолч. 300.0 сек) |

### MCPStreamableHTTPConfig

| Поле | Тип | Обязительное | Описание |
|------|-----|:---:|----------|
| `url` | `str` | Да | URL MCP-эндпоинта |
| `headers` | `dict[str, str] \| None` | Нет | Дополнительные HTTP-заголовки |
| `timeout` | `float` | Нет | Таймаут HTTP-запросов (по умолч. 5.0 сек) |

## Жизненный цикл клиента

```
DISCONNECTED → CONNECTING → INITIALIZED → TOOLS_DISCOVERED → CLOSED
                        ↘ ERROR ↗
```

- **DISCONNECTED** — начальное состояние
- **CONNECTING** — установка соединения с сервером
- **INITIALIZED** — рукопожатие протокола завершено
- **TOOLS_DISCOVERED** — инструменты обнаружены (после `list_tools()`)
- **ERROR** — ошибка подключения/инициализации
- **CLOSED** — клиент отключён

### Программное использование

```python
from graphrag_llm.mcp import MCPClient
from graphrag_llm.config import MCPConfig

async def main():
    config = MCPConfig(
        transport_type="stdio",
        stdio={"command": "python", "args": ["-m", "my_server"]},
    )

    async with MCPClient(config) as client:
        # Подключение и инициализация
        await client.connect()
        await client.initialize()

        # Обнаружение инструментов
        tools = await client.list_tools()
        print(f"Доступно инструментов: {len(tools)}")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")

        # Вызов инструмента
        result = await client.call_tool("echo", {"message": "Привет!"})
        print(result)

    # Автоматическое отключение
```

## Обработка ошибок

### Oшибки подключения

- `MCPConnectionError` — сбой подключения, потеря соединения
- `MCPTimeoutError` — превышен таймаут инициализации или вызова инструмента
- `MCPToolError` — ошибка выполнения инструмента

### Случай ошибки при вызове инструмента

```python
from graphrag_llm.mcp.client import MCPConnectionError, MCPToolError, MCPTimeoutError

try:
    result = await client.call_tool("some_tool", {"arg": "value"})
except MCPTimeoutError as e:
    print(f"Таймаут: {e}")
except MCPConnectionError as e:
    print(f"Потеря соединения: {e}")
except MCPToolError as e:
    print(f"Ошибка инструмента: {e}")
```

### Галлюцинации LLM

Если LLM вызывает инструмент, которого не существует, middleware возвращает LLM ошибку с перечнем доступных инструментов. LLM обычно исправляется и использует корректное имя.

## Отладка

### Включение логирования

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Включает подробное логирование MCP:
# - Подключение к серверу
# - Обнаруженные инструменты
# - Циклы вызова инструментов
# - Ошибки
```

### Распространённые проблемы

| Проблема | Решение |
|----------|---------|
| **Сервер не запускается** | Проверьте, что команда верна и исполняемый файл существует. Убедитесь, что аргументы соответствуют ожиданиям сервера |
| **Таймаут при инициализации** | Увеличьте `init_timeout`. Некоторые MCP-серверы требуют времени на запуск |
| **Инструмент не найден** | Убедитесь, что имя инструмента соответствует тому, что возвращает сервер. LLM может использовать неверное имя |
| **Соединение потеряно** | Для stdio проверьте, что subprocess всё ещё работает. Для SSE/HTTP — проверьте сетевое соединение |
| **Слишком много циклов** | Лимит — 10 итераций. Если LLM зацикливается на вызовах инструментов, уменьшите `max_iterations` в middleware или исправьте промпт |

## Пример: полный рабочий код

```python
import asyncio
from graphrag_llm.completion import OpenAICompletionFactory
from graphrag_llm.config import ModelConfig

def create_mcp_completion():
    mcp_config = {
        "mcp_config": {
            "transport_type": "stdio",
            "stdio": {
                "command": "python",
                "args": ["-m", "mcp_server"],
            },
            "init_timeout": 30.0,
            "tool_timeout": 30.0,
        }
    }

    model_config = ModelConfig(
        model_provider="openai",
        model="gpt-4o",
        api_key="sk-...",
        call_args=mcp_config,
    )

    return OpenAICompletionFactory(
        model_id="gpt-4o",
        model_config=model_config,
    )

def main():
    completion = create_mcp_completion()

    response = completion.completion(
        messages=[
            {"role": "system", "content": "Вы helpful ассистент с доступом к внешним инструментам."},
            {"role": "user", "content": "Запустите команду ls -la /tmp и покажите результат"},
        ],
    )

    print(response.content)

if __name__ == "__main__":
    main()
```

## Архитектура

```
packages/graphrag-llm/graphrag_llm/mcp/
├── __init__.py              # Публичные экспорты (MCPClient, MCPTool, middleware)
├── types.py                 # MCPTool — данные инструмента
├── config/
│   └── mcp_config.py        # MCPConfig, MCPStdioConfig, MCPSSEConfig, MCPStreamableHTTPConfig
├── transport.py             # MCPTransport ABC, StdioTransport, SSETransport, StreamableHTTPTransport
├── client.py                # MCPClient — управление жизненным циклом соединения
└── middleware.py            # MCPCompletionMiddleware — перехват LLM-завершений
```

Интеграция в пайплайн происходит через `with_middleware_pipeline()` — MCP-мидлвар вставляется между `with_retries` и `with_cache`.
