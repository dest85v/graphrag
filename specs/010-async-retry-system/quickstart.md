# Quickstart: Retry System Tests

## Run retry unit tests
```bash
uv run pytest packages/graphrag-llm/tests/unit/test_exponential_retry.py -v
```

## Run retry routing tests
```bash
uv run pytest packages/graphrag-llm/tests/unit/test_with_retries.py -v
```

## Run event loop responsiveness integration test
```bash
uv run pytest packages/graphrag-llm/tests/integration/test_retry_event_loop.py -v --run_slow
```

## Run all graphrag-llm tests
```bash
uv run pytest packages/graphrag-llm/tests/ -v
```

## Full check
```bash
uv run poe check
```

## Understanding the tests

### Unit tests (`test_exponential_retry.py`)
- `test_sync_retry_uses_time_sleep` — mocks `time.sleep`, verifies it's called
- `test_async_retry_uses_asyncio_sleep` — mocks `asyncio.sleep`, verifies it's called
- `test_retry_metrics_updated` — verifies metrics dict contents
- `test_max_retries_stops_retrying` — verifies retry limit

### Routing tests (`test_with_retries.py`)
- `test_sync_path_calls_retry` — verifies sync middleware routes to `retrier.retry()`
- `test_async_path_calls_retry_async` — verifies async middleware routes to `retrier.retry_async()`

### Integration test (`test_retry_event_loop.py`)
- `test_async_retry_does_not_block_event_loop` — spawns 5 concurrent coroutines, 1 triggers retry with 2s delay, verifies all complete within ~2.5s (not 10s sequential)
