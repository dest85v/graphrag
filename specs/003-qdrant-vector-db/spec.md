# Feature Specification: Qdrant Vector Store Support

**Feature Branch**: `003-003-qdrant-vector`
**Created**: 2026-04-17
**Status**: Draft
**Input**: User description: "Надо реализовать задачу 'P1 — Добавить поддержку Qdrant как 4-й векторной БД'"

## User Scenarios & Testing

### User Story 1 - Configure and Use Qdrant as Vector Backend (Priority: P1)

A GraphRAG operator wants to deploy GraphRAG with Qdrant as the vector storage backend instead of the default LanceDB. They need to be able to select Qdrant in their configuration and have the system transparently use it for all vector operations — indexing embeddings during ingestion and querying during search.

**Why this priority**: This is the core value proposition. Without Qdrant support, users who prefer Qdrant (for its mature filtering, remote deployment, or HNSW performance) cannot use GraphRAG with their preferred vector store. This unlocks a major deployment scenario.

**Independent Test**: An operator can configure `vector_store.type: qdrant` in their GraphRAG YAML, run the indexing workflow, and verify that entities and text units are stored in Qdrant and retrievable via similarity search.

**Acceptance Scenarios**:

1. **Given** a running Qdrant instance (local or cloud), **When** the user sets `vector_store.type: qdrant` with `url` and optionally `api_key` in configuration, **Then** the GraphRAG indexing pipeline stores embeddings in Qdrant without errors
2. **Given** embeddings are stored in Qdrant, **When** a query runs similarity search, **Then** results are retrieved from Qdrant with correct similarity scores and metadata
3. **Given** Qdrant is configured with metadata fields, **When** a filtered search is performed, **Then** Qdrant point filters correctly restrict results

---

### User Story 2 - Migrate Existing Workflows to Qdrant (Priority: P2)

An existing GraphRAG deployment wants to switch from LanceDB to Qdrant (or vice versa) without changing indexing logic, query code, or workflow definitions. The vector store should be interchangeable behind the same interface.

**Why this priority**: Users need confidence that adding Qdrant doesn't break existing LanceDB/Azure AI Search/CosmosDB deployments and that switching is a configuration change, not a code change.

**Independent Test**: A user can run the same GraphRAG index with `vector_store.type: lancedb` and with `vector_store.type: qdrant` and get equivalent result quality, proving the interface is consistent.

**Acceptance Scenarios**:

1. **Given** a GraphRAG project configured for LanceDB, **When** the user changes `type` to `qdrant` and provides Qdrant connection details, **Then** all existing workflows (text embeddings, entity search, local/global search) continue to work identically
2. **Given** multiple vector store types are registered, **When** the system creates a vector store instance, **Then** only the selected type is instantiated (no cross-contamination)

---

### User Story 3 - Leverage Qdrant-Specific Features (Priority: P3)

An operator running Qdrant at scale wants to benefit from Qdrant's native capabilities: HNSW index configuration for performance tuning, sparse vector support for hybrid search, and payload-based filtering on rich metadata.

**Why this priority**: These are advanced features that differentiate Qdrant from the other built-in stores. They are not required for basic functionality but are important for production-scale users.

**Independent Test**: An operator can configure custom HNSW parameters (e.g., `m`, `ef_construct`) and verify that search performance characteristics change accordingly.

**Acceptance Scenarios**:

1. **Given** Qdrant configuration includes custom HNSW parameters, **When** the index is created, **Then** Qdrant applies the specified HNSW configuration
2. **Given** documents have rich metadata payloads, **When** a filter is applied, **Then** Qdrant uses payload-based filtering natively

---

### Edge Cases

- What happens when Qdrant is unreachable during indexing? — The system should surface a clear error about Qdrant connectivity and fail fast
- How does the system handle Qdrant collection name conflicts? — The system should use the configured `index_name` and recreate/update the collection
- What if the vector size in config doesn't match the embedding model output? — Validation should catch dimension mismatch and fail with a clear message (already handled by `_sync_vector_store_dimensions` in `graphrag/index/validate_config.py`)
- How are large batches handled? — Documents should be batched in chunks (e.g., 100-500 points per upsert) to avoid Qdrant rate limits or payload size limits

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support Qdrant as a configurable vector store type alongside LanceDB, Azure AI Search, and CosmosDB
- **FR-002**: Users MUST be able to configure Qdrant via `vector_store.type: qdrant` in the GraphRAG YAML configuration
- **FR-003**: System MUST support both local Qdrant (via `localhost` URL) and Qdrant Cloud (via cloud URL + API key)
- **FR-004**: System MUST support all vector operations via Qdrant: connect, create index, load documents, vector similarity search, text similarity search, search by ID, count documents, remove documents, and update documents
- **FR-005**: System MUST support filter expressions via Qdrant point filters, supporting equality, inequality, range, IN, NOT IN, AND, OR, and NOT operators
- **FR-006**: System MUST support metadata payload fields with correct type mapping (str, int, float, bool)
- **FR-007**: System MUST support configurable HNSW index parameters (m, ef_construct, ef) for search performance tuning
- **FR-008**: System MUST batch document uploads to Qdrant to handle large embedding sets efficiently
- **FR-009**: System MUST include Qdrant client as an optional dependency installable independently of other vector store dependencies
- **FR-010**: System MUST discover and instantiate Qdrant automatically when selected as the vector store type
- **FR-011**: System MUST support Qdrant-specific configuration parameters (connection URL, API key, collection name, HNSW index settings, similarity distance metric)
- **FR-012**: System MUST maintain backward compatibility — existing LanceDB, Azure AI Search, and CosmosDB configurations MUST continue to work unchanged

### Key Entities

- **QdrantVectorStore**: The Qdrant implementation of the VectorStore ABC. Manages connection to Qdrant, collection lifecycle, and all vector operations.
- **Qdrant Configuration Fields**: Additional fields in VectorStoreConfig for Qdrant — `url` (connection point), `api_key` (Qdrant Cloud auth), `collection_name` (logical index name), `hnsw_cfg` (HNSW index configuration object), `distance` (similarity metric: cosine, dot, euclidean).
- **Collection**: The Qdrant logical container for vectors and payloads, analogous to a table in LanceDB or an index in Azure AI Search.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can configure and use Qdrant as the vector backend within 5 minutes of reading documentation
- **SC-002**: Vector search returns results with high accuracy (similarity score correlation > 0.95 against reference implementation using identical embeddings)
- **SC-003**: Qdrant supports indexing 100,000+ vectors with metadata in under 5 minutes via batched uploads
- **SC-004**: All existing GraphRAG workflows (indexing, local search, global search, drift search) function correctly with Qdrant without code changes
- **SC-005**: Adding Qdrant as a vector store type does not introduce regressions in existing vector store backends (all existing integration tests pass unchanged)
- **SC-006**: Filter expressions produce identical results across all vector store backends for the same query and filter conditions

## Assumptions

- The Qdrant Python client (`qdrant-client`) is the standard SDK and will be used for all Qdrant interactions
- Qdrant 1.7+ is the minimum supported version (stable API, supports all needed features)
- Local Qdrant deployment (via Docker) is the default development/testing scenario; Qdrant Cloud is a first-class supported option
- The existing `VectorStore` ABC, `VectorStoreConfig`, `VectorStoreFactory`, and `FilterExpr` infrastructure will be reused — no changes to the base interface
- Metadata field types (str, int, float, bool) map directly to Qdrant payload types
- HNSW index is the default and only ANN index type; simple index or discarding are out of scope for v1
- Distance metric defaults to cosine (matching existing LanceDB default); dot product and euclidean are configurable
