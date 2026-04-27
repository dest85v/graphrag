# Quickstart: Verify Exception Logging Fix

## Run middleware unit tests

```bash
uv run pytest packages/graphrag-llm/tests/unit/ -v -k "cache"
```

## Run MCP middleware tests

```bash
uv run pytest packages/graphrag-llm/tests/unit/ -v -k "mcp"
```

## Run global search tests

```bash
uv run pytest packages/graphrag/tests/ -v -k "global"
```

## Run all graphrag-llm tests

```bash
uv run pytest packages/graphrag-llm/tests/ -v
```

## Run full check

```bash
uv run poe check
```

## Run all tests

```bash
uv run poe test
```

## Verify logging output

After changes, simulate a cache failure and verify logs contain:
- `ERROR:graphrag_llm.middleware.with_cache:Failed to parse cached response...` (already present)
- `ERROR:graphrag_llm.middleware.with_cache:...` for cache write failures (new)
- `ERROR:graphrag_llm.mcp.middleware:...` for unexpected MCP tool errors (new)
