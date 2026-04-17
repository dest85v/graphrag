# Research: Qdrant Vector Store Integration

## Decision 1: Qdrant Client Library Version

**Decision**: Use `qdrant-client>=1.7.0,<1.18.0`

**Rationale**: 
- Qdrant 1.7.0 introduced stable `query_points()` API (replacing deprecated `search()`) and stable `Filter`/`FieldCondition` filter composition
- Latest stable is 1.17.1 (March 2026) — well-tested and actively maintained
- `qdrant-client` is Apache 2.0 licensed, same as GraphRAG
- Python 3.10+ compatible (project requires 3.11+)

**Alternatives considered**:
- `qdrant-client>=1.6.0`: Would include deprecated `search()` API — avoided
- `qdrant-client>=1.8.0`: Newer features unnecessary for v1, adds risk
- Pinning to exact version: Avoided to allow security patch updates

## Decision 2: Connection Pattern (REST vs gRPC)

**Decision**: Default to REST (`QdrantClient(url=...)`), support `prefer_grpc=True` via config

**Rationale**:
- REST is the universal transport — works with local, Docker, and Qdrant Cloud
- gRPC is 10-100x faster for bulk uploads but requires `grpc_port` configuration
- Existing stores (LanceDB, Azure AI Search, CosmosDB) use synchronous REST-like connections
- Users can enable gRPC via a `prefer_grpc` config field if needed

**Alternatives considered**:
- Default to gRPC: Too restrictive — Qdrant Cloud requires REST for some operations
- Always use `upload_collection()` for large batches: Good optimization but adds complexity; `upsert()` with `Batch` is sufficient for typical GraphRAG batch sizes (hundreds to low thousands of embeddings per workflow run)

## Decision 3: Filter Expression Compilation

**Decision**: Map existing `FilterExpr` (Condition, AndExpr, OrExpr, NotExpr) to Qdrant `Filter`/`FieldCondition`

**Rationale**:
- Qdrant's `Filter(must=[...], should=[...], must_not=[...])` maps directly to AND/OR/NOT
- `Condition.eq`, `Condition.ne`, `Condition.gt`, `Condition.gte`, `Condition.lt`, `Condition.lte` → `FieldCondition(match=MatchValue(...))` or `FieldCondition(range=Range(...))`
- `Condition.in_` → `FieldCondition(match=MatchAny(any=[...]))`
- `Condition.not_in` → `Filter(must_not=[FieldCondition(match=MatchAny(any=[...]))])`
- `Condition.contains` → `FieldCondition(match=MatchText(text=...))`
- `Condition.startswith`/`Condition.endswith` → `MatchText` with wildcards or `MatchAny`
- `Condition.exists` → `IsNullCondition`/`IsNotNullCondition`

**Pattern**: Follow the exact same structure as `LanceDBVectorStore._compile_filter()` and `_compile_condition()` — a match statement that delegates to per-operator handlers.

**Alternatives considered**:
- Build Qdrant native filters from scratch: Unnecessary duplication — the existing `FilterExpr` types are the abstraction
- Reverse-compile Qdrant filters to SQL-like strings: More fragile, loses type safety

## Decision 4: Payload Type Mapping

**Decision**: Python → Qdrant payload types as follows:

| Python type (from `fields` dict) | Qdrant payload type | Mapping |
|---|---|---|
| `str` | `string` | `str(value)` |
| `int` | `integer` | `int(value)` |
| `float` | `float` | `float(value)` |
| `bool` | `boolean` | `bool(value)` |

**Rationale**: Direct one-to-one mapping — same as LanceDB and existing stores. Qdrant infers payload types from Python values automatically.

**Alternatives considered**:
- Explicit type declarations per field: Qdrant infers from Python values; unnecessary complexity
- Timestamp-aware types for date fields: Handle at the `VectorStore._prepare_document()` level (already done in base ABC)

## Decision 5: HNSW Configuration

**Decision**: Provide `HnswConfigDiff`-based configuration with sensible defaults

**Rationale**:
- Default HNSW params: `m=16`, `ef_construct=100`, `full_scan_threshold=10000` (Qdrant defaults)
- These match the quality/performance trade-off used by LanceDB's IVF_FLAT
- Advanced users can override via config fields: `hnsw_m`, `hnsw_ef_construct`, `hnsw_ef` (search-time `ef`)
- `ef` (search-time) should be configurable — higher values = better recall but slower search

**Alternatives considered**:
- Expose full `HnswConfigDiff`: Overwhelming for typical users
- No HNSW customization in v1: Limits power users; adding 3 fields is low cost

## Decision 6: Distance Metric

**Decision**: Default to `Distance.COSINE`, configurable via `distance` field

**Rationale**:
- Cosine similarity is the de facto default for text embeddings (matches LanceDB default)
- Qdrant supports: COSINE, DOT, EUCLID, MANHATTAN
- Users select via `vector_store.distance: cosine|dot|euclidean|manhattan`

**Alternatives considered**:
- Fixed to COSINE: Limits users who need DOT for non-normalized embeddings
- Auto-detect from embedding model: No standard way to determine this

## Decision 7: Batch Upload Strategy

**Decision**: Use `upsert()` with `Batch` for documents, chunking at 1000 points per batch

**Rationale**:
- `upload_collection()` is optimized for raw arrays (numpy), not `VectorStoreDocument` objects
- `upsert()` with `Batch(ids=..., vectors=..., payloads=...)` is the right API for `VectorStoreDocument`-based flow
- Chunk size of 1000 balances throughput and memory: small enough to avoid large payloads, large enough for good throughput
- Aligns with existing patterns: LanceDB uses PyArrow batch writes, Azure AI Search uses batch upload, CosmosDB uses individual upserts

**Alternatives considered**:
- Chunk size 64 (Qdrant default for `upload_collection`): Too small for efficient GraphRAG workflows
- Chunk size 5000+: Risk of hitting Qdrant payload size limits on dense metadata

## Decision 8: Test Strategy

**Decision**: Use in-memory Qdrant (`:memory:`) for unit tests, Docker Qdrant for integration tests

**Rationale**:
- `QdrantClient(":memory:")` provides a fully functional Qdrant instance with no external dependencies — ideal for unit tests
- Integration tests use a Docker-based Qdrant (same pattern as Azurite for Azure storage tests)
- Mirrors existing test patterns: `test_lancedb.py` uses `tempfile.mkdtemp()` for file-based storage; Qdrant `:memory:` is the equivalent

**Alternatives considered**:
- Integration tests only: Slower CI, requires Docker in CI
- Unit tests only: Misses real Qdrant behavior (filter compilation, batch upload edge cases)

## Decision 9: Collection Lifecycle

**Decision**: Recreate collection on `create_index()` (overwrite semantics)

**Rationale**:
- Matches existing `LanceDBVectorStore.create_index()` behavior: drops and recreates
- `LanceDBVectorStore.create_index()` removes the dummy document after schema creation
- Qdrant: `delete_collection()` + `create_collection()` on each `create_index()` call
- Simpler than merge/append semantics; GraphRAG workflows always re-index from scratch

**Alternatives considered**:
- Append-only: Would require deduplication logic; unnecessary for GraphRAG's re-index pattern
- Conditional create (create if not exists): Risk of stale data between runs
