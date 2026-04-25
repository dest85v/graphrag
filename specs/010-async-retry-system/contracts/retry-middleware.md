# Retry Middleware Contract

## Interface: `with_retries()`

**Package**: `graphrag-llm`  
**Module**: `graphrag_llm.middleware.with_retries`

### Function Signature

```python
def with_retries(
    *,
    sync_middleware: LLMFunction,
    async_middleware: AsyncLLMFunction,
    retrier: Retry,
) -> tuple[LLMFunction, AsyncLLMFunction]:
```

### Returns

A tuple of two wrapper functions:

1. **Sync wrapper** `( **kwargs: Any ) -> Any`
   - Calls `retrier.retry(func=sync_middleware, input_args=kwargs)`
   - Uses `time.sleep()` for backoff delays (blocking, correct for sync)

2. **Async wrapper** `( **kwargs: Any ) -> Awaitable[Any]`
   - Calls `await retrier.retry_async(func=async_middleware, input_args=kwargs)`
   - Uses `await asyncio.sleep()` for backoff delays (non-blocking, correct for async)

### Invariants

| Invariant | Enforcement |
|---|---|
| Sync path must use `time.sleep()` | Verified by unit test mocking `time.sleep` |
| Async path must use `await asyncio.sleep()` | Verified by unit test mocking `asyncio.sleep` |
| Metrics dict updated in both paths | `retries` count, `requests_with_retries` boolean flag |
| No side effects when no retry needed | First-success returns immediately |

## Interface: `Retry` ABC

**Package**: `graphrag-llm`  
**Module**: `graphrag_llm.retry.retry`

### Abstract Methods

```python
class Retry(ABC):
    def retry(self, *, func: Callable[..., Any], input_args: dict[str, Any]) -> Any:
        """Retry a synchronous function. Uses time.sleep() for backoff."""
    
    async def retry_async(
        self,
        *,
        func: Callable[..., Awaitable[Any]],
        input_args: dict[str, Any],
    ) -> Any:
        """Retry an asynchronous function. Uses await asyncio.sleep() for backoff."""
```

### Concrete Implementations

| Class | Backoff | Sleep in sync path | Sleep in async path |
|---|---|---|---|
| `ExponentialRetry` | Exponential + jitter | `time.sleep()` | `await asyncio.sleep()` |
| `ImmediateRetry` | None (immediate) | N/A | N/A |

### Backoff Calculation (ExponentialRetry)

```
delay = 1.0
for each retry:
    delay *= base_delay
    sleep_delay = min(max_delay, delay + (jitter * random.uniform(0, 1)))
    # sync: time.sleep(sleep_delay)
    # async: await asyncio.sleep(sleep_delay)
```

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `max_retries` | `int` | 7 | Maximum retry attempts (2^7 = 128s with defaults) |
| `base_delay` | `float` | 2.0 | Base delay multiplier in seconds |
| `jitter` | `bool` | True | Whether to add random jitter |
| `max_delay` | `float \| None` | None | Maximum delay cap (no cap if None) |
| `exceptions_to_skip` | `list[str]` | default list | Exception class names that skip retry |
