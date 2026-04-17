# Contract: VectorStore Interface (Qdrant Implementation)

## Overview

This document defines the contract that `QdrantVectorStore` must fulfill by implementing the `VectorStore` abstract base class. The contract ensures interchangeability between all vector store backends (LanceDB, Azure AI Search, CosmosDB, Qdrant).

## Abstract Method Contracts

### `connect() -> None`

Establishes connection to the Qdrant server and initializes the internal client.

**Qdrant-specific behavior**:
- Creates `QdrantClient(url=..., api_key=...)` or `QdrantClient(path=:memory:)` for local testing
- Sets `_client` instance attribute
- No collection creation happens here — that's `create_index()` responsibility

**Error conditions**:
- Raises `ValueError` if `url` is not provided (for remote Qdrant)
- Raises `ConnectionError` if Qdrant server is unreachable (propagated to caller)

**Example**:
```python
store = QdrantVectorStore(url="http://localhost:6333", vector_size=1536)
store.connect()  # _client = QdrantClient(url="http://localhost:6333")
```

---

### `create_index() -> None`

Creates (or recreates) the Qdrant collection with the configured schema.

**Qdrant-specific behavior**:
- Deletes existing collection if present (overwrite semantics)
- Creates collection with:
  - `VectorParams(size=vector_size, distance=<distance>)`
  - Optional `HnswConfigDiff(m=hnsw_m, ef_construct=hnsw_ef_construct)` if configured
- Collection name = `self.index_name`

**Error conditions**:
- Raises `ValueError` if `index_name` is empty

**Example**:
```python
store.create_index()
# Qdrant collection "my_collection" created with 1536-dim cosine vectors
```

---

### `load_documents(documents: list[VectorStoreDocument]) -> None`

Batch-loads documents into Qdrant as points with vectors and payloads.

**Qdrant-specific behavior**:
- Builds a list of `PointStruct(id=..., vector=..., payload=...)` from documents
- Documents with `vector=None` are skipped
- Batches are sent via `client.upsert(collection_name=..., points=batch)`
- Default batch size: 1000 points per upsert call

**Error conditions**:
- Empty document list: no-op (no error)
- Documents with `vector=None`: silently skipped (consistent with existing stores)

**Example**:
```python
docs = [
    VectorStoreDocument(id="1", vector=[0.1, 0.2, 0.3], data={"title": "Doc 1"}),
    VectorStoreDocument(id="2", vector=[0.4, 0.5, 0.6], data={"title": "Doc 2"}),
]
store.load_documents(docs)
# Two points upserted to Qdrant collection
```

---

### `similarity_search_by_vector(query_embedding: list[float], k: int = 10, select: list[str] | None = None, filters: FilterExpr | None = None, include_vectors: bool = True) -> list[VectorStoreSearchResult]`

Performs ANN vector search with optional filtering.

**Qdrant-specific behavior**:
- Calls `client.query_points()` (modern API, not deprecated `search()`)
- Converts `FilterExpr` to Qdrant `Filter` via `_compile_filter()`
- Query vector passed as raw `list[float]`
- `score` in result = raw Qdrant score (converted to 0–1 range where applicable)
- `select` limits returned payload fields
- `include_vectors=False` omits vector from results

**Score normalization**:
- Cosine: Qdrant returns raw cosine similarity (already 0–1 for normalized vectors)
- DOT: Qdrant returns raw dot product
- EUCLID: Qdrant returns negative Euclidean distance (negate for similarity)

**Example**:
```python
results = store.similarity_search_by_vector(
    query_embedding=[0.1, 0.2, 0.3],
    k=5,
    filters=F.category == "tech",
    include_vectors=True,
)
# Returns up to 5 VectorStoreSearchResult objects
```

---

### `similarity_search_by_text(text: str, text_embedder: TextEmbedder, k: int = 10, select: list[str] | None = None, filters: FilterExpr | None = None, include_vectors: bool = True) -> list[VectorStoreSearchResult]`

Text-based similarity search (embeds text, then searches by vector).

**Qdrant-specific behavior**:
- Delegates to `similarity_search_by_vector()` after embedding
- Same contract as base `VectorStore.similarity_search_by_text()`

**Example**:
```python
def embedder(text: str) -> list[float]:
    return model.encode(text).tolist()

results = store.similarity_search_by_text("AI in healthcare", embedder, k=10)
```

---

### `search_by_id(id: str, select: list[str] | None = None, include_vectors: bool = True) -> VectorStoreDocument`

Retrieves a single document by ID.

**Qdrant-specific behavior**:
- Calls `client.retrieve(collection_name=..., ids=[id], ...)`
- Returns single `VectorStoreDocument`
- Raises `IndexError` if document not found (consistent with `LanceDBVectorStore`)

**Example**:
```python
doc = store.search_by_id("123")
assert doc.id == "123"
```

---

### `count() -> int`

Returns the total number of points in the collection.

**Qdrant-specific behavior**:
- Calls `client.count(collection_name=..., exact=True)`
- Returns `count_result.count`

**Example**:
```python
n = store.count()
assert n == 10000
```

---

### `remove(ids: list[str]) -> None`

Removes points by ID list.

**Qdrant-specific behavior**:
- Calls `client.delete(collection_name=..., points=ids)`
- Supports both integer and string IDs (Qdrant native)

**Example**:
```python
store.remove(["1", "2", "3"])
```

---

### `update(document: VectorStoreDocument) -> None`

Updates a point's vector and/or payload.

**Qdrant-specific behavior**:
- Reads existing point via `retrieve()`
- Merges update: `update_date`, vector (if provided), data fields (if provided)
- Upserts the merged point via `upsert()`
- `set_payload()` alternative for payload-only updates considered but not used (simpler to read-merge-upsert)

**Example**:
```python
store.update(VectorStoreDocument(id="1", vector=[0.9, 0.8, 0.7], data={"title": "Updated"}))
```

---

## Filter Expression Mapping

All `FilterExpr` types are compiled to Qdrant `Filter` objects:

| FilterExpr | Qdrant Equivalent |
|---|---|
| `Condition.eq(field, value)` | `Filter(must=[FieldCondition(key=field, match=MatchValue(value))])` |
| `Condition.ne(field, value)` | `Filter(must_not=[FieldCondition(key=field, match=MatchValue(value))])` |
| `Condition.gt(field, value)` | `Filter(must=[FieldCondition(key=field, range=Range(gt=value))])` |
| `Condition.gte(field, value)` | `Filter(must=[FieldCondition(key=field, range=Range(gte=value))])` |
| `Condition.lt(field, value)` | `Filter(must=[FieldCondition(key=field, range=Range(lt=value))])` |
| `Condition.lte(field, value)` | `Filter(must=[FieldCondition(key=field, range=Range(lte=value))])` |
| `Condition.in_(field, values)` | `Filter(must=[FieldCondition(key=field, match=MatchAny(any=values))])` |
| `Condition.not_in(field, values)` | `Filter(must_not=[FieldCondition(key=field, match=MatchAny(any=values))])` |
| `Condition.contains(field, value)` | `Filter(must=[FieldCondition(key=field, match=MatchText(text=value))])` |
| `Condition.startswith(field, value)` | `Filter(must=[FieldCondition(key=field, match=MatchText(text=f"{value}*"))])` |
| `Condition.endswith(field, value)` | `Filter(must=[FieldCondition(key=field, match=MatchText(text=f"*{value}"))])` |
| `Condition.exists(field, value)` | `IsNullCondition(key=field)` if `not value`, else `IsNotNullCondition(key=field)` |
| `AndExpr(and_)` | `Filter(must=[compiled(and_)])` |
| `OrExpr(or_)` | `Filter(should=[compiled(or_)])` |
| `NotExpr(not_)` | `Filter(must_not=[compiled(not_)])` |

## Configuration Contract

Qdrant-specific configuration fields are passed through `VectorStoreConfig` extras:

```python
# This config is valid:
config = VectorStoreConfig(
    type="qdrant",
    url="http://localhost:6333",
    api_key="optional-key",
    distance="cosine",
    hnsw_m=32,
    hnsw_ef_construct=256,
    hnsw_ef=512,
    vector_size=1536,
    index_schema={
        "entities": IndexSchema(index_name="entities", fields={"label": "str"}),
    },
)
```
