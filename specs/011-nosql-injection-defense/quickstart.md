# Quickstart: NoSQL Injection Defense

## Purpose

Verify the NoSQL injection defense implementation without setting up a real Cosmos DB instance.

## Prerequisites

- Python 3.11–3.13
- `uv` installed
- Repository cloned and deps synced: `uv sync`

## Verification Steps

### 1. Run sanitizer unit tests

These tests verify the `_sanitize_cosmos_key()` function correctly escapes special characters.

```bash
uv run poe test_only "test_cosmos_sanitizer"
```

**Expected**: All tests pass, including:
- Normal strings pass through unchanged
- Strings with `'` are escaped (doubled)
- Strings with `\` are escaped (doubled)
- Strings with `"` are escaped (escaped with backslash)
- NoSQL injection payloads (`entities'; DROP DATABASE --`) are neutralized
- Unicode characters are preserved unchanged

### 2. Run security injection tests

These tests use mocked CosmosDB clients to verify that query strings are properly sanitized at all construction points.

```bash
uv run poe test_only "test_cosmos_storage_security"
uv run poe test_only "test_cosmos_vector_security"
```

**Expected**: All tests pass, including:
- `AzureCosmosStorage.load()` with malicious key → sanitized prefix in query
- `AzureCosmosStorage.delete()` with malicious key → sanitized prefix in query
- `AzureCosmosStorage.count()` with malicious filter → sanitized filter in query
- `CosmosDBVectorStore.similarity_search_by_vector()` with malicious field name → rejected at init
- `CosmosDBVectorStore._compile_condition()` with malicious string value → escaped in query
- All existing valid inputs work identically (backward compatibility)

### 3. Run full test suite (regression check)

```bash
uv run poe test_unit
uv run poe test_integration
```

**Expected**: All existing tests pass with zero regressions. No new failures.

### 4. Run full quality check

```bash
uv run poe check
```

**Expected**: Format, lint, and typecheck all pass with zero errors.

## Manual Testing (Optional)

To manually verify sanitization behavior:

```python
from graphrag_storage.cosmos_sanitizer import _sanitize_cosmos_key

# Normal file name — unchanged
assert _sanitize_cosmos_key("entities.parquet") == "entities.parquet"

# File name with apostrophe — escaped
assert _sanitize_cosmos_key("file's name") == "file''s name"

# Malicious injection — neutralized
payload = "entities'; DROP DATABASE --"
sanitized = _sanitize_cosmos_key(payload)
assert "'" not in sanitized or sanitized == "entities''; DROP DATABASE --"

# Use in query — safe
query = f"SELECT * FROM c WHERE STARTSWITH(c.id, '{sanitized}:')"
# Result: SELECT * FROM c WHERE STARTSWITH(c.id, 'entities''; DROP DATABASE --:')
# The injected DROP is contained within the string literal — not executed
```

## Rollback

If issues are found, the changes are localized to:
- New files: `cosmos_sanitizer.py` (2 packages), test files (3 files)
- Modified files: `azure_cosmos_storage.py`, `cosmosdb.py`

All changes are additive (new functions, new validations) — no existing logic is removed.

## CI Integration

The tests are automatically run on every PR via:
- `uv run poe test_unit` — includes sanitizer tests
- `uv run poe check` — includes format/lint/typecheck for new files

No additional CI configuration is needed.
