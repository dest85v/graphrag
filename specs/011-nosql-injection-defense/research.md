# Research: NoSQL Injection in Cosmos DB SQL API

## Purpose

Resolve all technical unknowns and design decisions for the NoSQL injection defense feature.

## Research Tasks & Findings

### 1. Cosmos DB SQL API Query Injection Vectors

**Question**: What are the actual injection vectors in Cosmos DB SQL API, and how does string escaping work?

**Findings**:
- Cosmos DB SQL API uses double-quoted strings in query literals: `WHERE STARTSWITH(c.id, 'value')`
- The `STARTSWITH()`, `CONTAINS()`, `ENDSWITH()` functions accept string literals
- Single quotes in string literals must be escaped by doubling them: `'it''s'` → `it's`
- Backslashes are escape characters in SQL string literals: `\\` → literal `\`, `\"` → literal `"`
- NoSQL injection typically uses:
  - **String termination**: `' OR 1=1 --` — the `'` closes the string literal, `OR 1=1` is a new predicate
  - **Statement termination**: `'; DROP DATABASE --` — `;` ends the statement, new statement follows
  - **Comment bypass**: `--` or `/* */` comments out remaining query
- **Mitigation**: Escape `\` → `\\` and `"` → `\"` (for double-quoted fields) and `'` → `''` (for single-quoted literals). In our code, all string interpolations use single quotes, so `'` → `''` is the critical escape.

**Decision**: The sanitizer MUST escape: `\` → `\\`, `"` → `\"`, and `'` → `''`. This covers all three injection vectors.

### 2. Cosmos DB Parameterized Query Support

**Question**: Can we use parameterized queries instead of string interpolation?

**Findings**:
- Cosmos DB SQL API supports parameterized values via `@param` syntax in `query_items()`
- Parameters work with: comparison operators (`=`, `>`, `<`, `>=`, `<=`, `!=`), `IN`, `VectorDistance()`
- Parameters do **NOT** work with: `STARTSWITH()`, `CONTAINS()`, `ENDSWITH()` string function arguments when the function needs a literal prefix
- The `query_items()` API accepts a `parameters` list: `[{"name": "@param", "value": "..."}]`
- However, even with parameters, `STARTSWITH(c.id, @prefix)` — this actually DOES work in Cosmos DB!

**Revised Decision**: For `similarity_search_by_vector()`, the filter compilation already uses string literals. The `_compile_filter()` method for `Condition` operators should be updated to use parameterized values where supported. However, for the `STARTSWITH` prefix queries in `azure_cosmos_storage.py`, we should check if `STARTSWITH(c.id, @prefix)` with a parameter works.

**Research follow-up**: Cosmos DB documentation confirms `STARTSWITH`, `CONTAINS`, and `ENDSWITH` DO accept parameterized values. This means we can use `@param` for all string values instead of escaping.

**Updated approach**: 
1. For storage layer (`azure_cosmos_storage.py`): Replace string interpolation with parameterized queries using `@prefix` for `STARTSWITH` calls
2. For vector store (`cosmosdb.py`): Replace string interpolation in field selections with validation-only (field names can't be parameterized, so validation is required)
3. Keep the sanitizer as a defense-in-depth measure for any remaining string literals

### 3. Pydantic v2 Validation Patterns

**Question**: What is the idiomatic Pydantic v2 pattern for field name validation?

**Findings**:
- Pydantic v2 uses `@field_validator` decorator for custom field validation
- Pattern: `@field_validator('id_field')` + `def validate_id_field(cls, v): ... return v`
- For `model_config` with `arbitrary_types_allowed = False`, validation happens at model construction
- Error messages: `raise ValueError("id_field must match pattern ...")`
- The `CosmosDBVectorStore` inherits from `VectorStore` which may or may not be a Pydantic model — need to verify

**Decision**: 
- For `CosmosDBVectorStore`: Validation in `__init__` using `re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*', value)` — simpler, no Pydantic dependency on the base class
- For `AzureCosmosStorage`: This is not a Pydantic model — validation in `__init__` for relevant config fields

### 4. Existing Filter Compilation Safety

**Question**: Is the existing `_compile_filter()` in `cosmosdb.py` safe from injection?

**Findings**:
- `_compile_condition()` in `cosmosdb.py` handles `Condition` values — these come from user-provided filter expressions
- String values in conditions are quoted with single quotes: `f"'{v}'" if isinstance(v, str)` — this IS vulnerable to injection if the value contains `'`
- Numeric values are passed as `str(v)` — safe from injection
- The `quote()` helper function does NOT escape single quotes — this is a vulnerability

**Decision**: The sanitizer MUST be applied to all string values in `_compile_condition()` via the `quote()` helper. This is a separate vulnerability from the prefix/field name issues.

### 5. Test Strategy for Mocked CosmosDB

**Question**: How to test sanitization without a real Cosmos DB instance?

**Findings**:
- `ContainerProxy` is a thin wrapper — can be mocked with `unittest.mock.MagicMock`
- Key test: construct query string, assert that injection payloads are escaped/sanitized
- For vector store: mock `_container_client.query_items()` to capture the query string, then assert sanitization
- For storage: similar mocking of `self._container_client.query_items()`
- No need for Azurite or Cosmos DB emulator — pure string assertion tests

**Decision**: Use `unittest.mock.patch` and `MagicMock` to capture query strings and assert sanitization. No external dependencies needed.

## Consolidated Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Sanitization strategy | Escape `\` → `\\`, `"` → `\"`, `'` → `''` | Defense-in-depth; works for all query patterns |
| Parameterized queries | Use `@param` for `STARTSWITH` prefix queries in storage layer | Cosmos DB supports this; cleaner than escaping |
| Field name validation | Regex `[a-zA-Z_][a-zA-Z0-9_]*` at init time | Field names can't be parameterized; must be safe identifiers |
| Filter value escaping | Apply sanitizer to all string values in `_compile_condition().quote()` | String values in conditions are currently unescaped |
| Utility placement | Per-package private module | Trivial function (3 lines), avoids cross-package dependency |
| Logging level | `WARNING` when sanitization occurs | Visible but not alarming; operator needs awareness |
| Test approach | Mocked `ContainerProxy` with string assertions | No external dependencies; fast CI |
| Backward compatibility | Zero breaking changes | Existing valid inputs work exactly as before |

## References

- [Azure Cosmos DB SQL API — Query Functions](https://learn.microsoft.com/en-us/azure/cosmos-db/nosql/query/functions?tabs=python)
- [Azure Cosmos DB SQL API — Parameterized Queries](https://learn.microsoft.com/en-us/azure/cosmos-db/nosql/query/query-parameters)
- [OWASP NoSQL Injection](https://owasp.org/www-community/attacks/No_SQL_injection)
