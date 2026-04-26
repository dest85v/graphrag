# Data Model: NoSQL Injection Defense

## Purpose

Document the data entities and validation rules relevant to the NoSQL injection defense feature.

## Overview

This feature does not introduce new data entities or storage schema changes. It modifies the **handling** of existing string values at query construction time. The data model below documents the entities, their roles in query construction, and the validation/sanitization rules applied.

## Entities

### Storage Key

Represents a file name or document identifier used as a Cosmos DB item key.

| Attribute | Type | Validation | Notes |
|---|---|---|---|
| `value` | `str` | Sanitized via `_sanitize_cosmos_key()` before query interpolation | May contain any Unicode characters; sanitization escapes `\`, `"`, `'` |
| `source` | `str` | None | Origin of the key (file name, path, configuration) — for debugging |

**Invariants**:
- The original value is preserved internally; sanitization is applied only at query construction
- Sanitization is idempotent: applying it twice produces the same result as applying it once for escape characters
- The sanitized value is logged (not the original) when escaping occurs

### Field Name

Represents a configurable identifier used in Cosmos DB query SELECT/WHERE clauses.

| Attribute | Type | Validation | Notes |
|---|---|---|---|
| `value` | `str` | Must match `[a-zA-Z_][a-zA-Z0-9_]*` (full match) | Validated at configuration time; rejected before any query execution |
| `purpose` | `str` | Enum: `id`, `vector`, `metadata`, `timestamp` | Identifies the role of the field (e.g., `id_field`, `vector_field`) |

**Invariants**:
- Field names must be valid Python/Cosmos DB identifier characters
- No escaping is applied — invalid field names are rejected outright
- Existing valid field names (`id`, `vector`, `create_date`, `update_date`, `title`, `text`) all match the pattern

### Query Filter

Represents a WHERE clause fragment built from filter expressions.

| Attribute | Type | Validation | Notes |
|---|---|---|---|
| `expression` | `FilterExpr` | Type-checked (AndExpr, OrExpr, NotExpr, Condition) | AST-like structure, not user input directly |
| `compiled_sql` | `str` | All string values escaped via `_sanitize_cosmos_key()` | Output of `_compile_filter()` |

**Invariants**:
- Filter expressions are constructed programmatically, not from raw user input
- String values within conditions are escaped via the sanitizer in the `quote()` helper
- Logical operators (AND, OR, NOT) are hard-coded and cannot be injected

### Filter Value

Represents a single value within a `Condition` expression.

| Attribute | Type | Validation | Notes |
|---|---|---|---|
| `value` | `str` \| `int` \| `float` \| `bool` \| `list` | Strings escaped via `_sanitize_cosmos_key()` in `quote()` helper | Non-string values are converted via `str()` — safe from injection |

**Invariants**:
- Only string values require escaping (they are quoted in SQL)
- Numeric values are safe: `str(123)` cannot be injection
- List values (for `IN` operator) have each element individually escaped

## Validation Flow

```
User/Config Input
       │
       ▼
┌─────────────────────┐
│ Is it a field name?  │──── Yes ──→ Validate [a-zA-Z_][a-zA-Z0-9_]* ──→ Reject if invalid
└─────────┬───────────┘
          │ No
          ▼
┌─────────────────────┐
│ Is it a query value? │──── Yes ──→ Apply _sanitize_cosmos_key() ──→ Log if escaped
└─────────┬───────────┘
          │
          ▼
    Safe Query String
```

## Relationships

- **Storage Key** → used in: `STARTSWITH(c.id, '{prefix}:')` queries in `azure_cosmos_storage.py`
- **Field Name** → used in: `c.{field}` interpolations in SELECT clauses in `cosmosdb.py`
- **Filter Value** → used in: `Condition` values compiled via `_compile_condition()` in `cosmosdb.py`

## Changes from Current State

| Entity | Before | After |
|---|---|---|
| Storage Key | Interpolated directly into queries | Sanitized via `_sanitize_cosmos_key()` |
| Field Name | No validation | Validated against identifier pattern at init time |
| Query Filter | String values unescaped in `quote()` | String values escaped via `_sanitize_cosmos_key()` |
