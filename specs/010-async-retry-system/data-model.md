# Data Model: Retry System

**Feature**: 010-async-retry-system  
**Note**: No new data entities. This section documents existing data structures for reference.

## Existing Entities

### Retry Metrics (dict)

Passed via `input_args["metrics"]` to both `retry()` and `retry_async()`.

| Key | Type | Description |
|---|---|---|
| `retries` | `int` | Number of retry attempts made |
| `requests_with_retries` | `int` | 1 if any retries occurred, 0 otherwise |

### ExponentialRetry Configuration

| Field | Type | Default | Description |
|---|---|---|---|
| `_base_delay` | `float` | 2.0 | Base delay multiplier |
| `_jitter` | `bool` | True | Enable random jitter |
| `_max_retries` | `int` | 7 | Maximum retry count |
| `_max_delay` | `float` | inf | Maximum delay cap |
| `_exceptions_to_skip` | `list[str]` | default list | Exception names to skip |

## State Transitions

The retry loop has no persistent state — it operates as a local loop variable:

```
retries = 0 → retries += 1 (on each exception) → retries >= max_retries (exit)
```

No state crosses function boundaries. The `metrics` dict is the only external side effect.
