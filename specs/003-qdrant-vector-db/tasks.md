---

description: "Task list for Qdrant vector store support"

---

# Tasks: Qdrant Vector Store Support

**Input**: Design documents from `/specs/003-qdrant-vector-db/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: REQUIRED — Constitution Principle III (Test-First, NON-NEGOTIABLE) mandates tests be written before implementation code.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add optional dependency extra and create test directory structure

- [x] T001 [P] Add `qdrant` optional dependency extra to `packages/graphrag-vectors/pyproject.toml` — add `[project.optional-dependencies] qdrant = ["qdrant-client>=1.7.0,<1.18.0"]` with comment linking to research.md decision 1
- [x] T002 Create test directories: `packages/graphrag-vectors/tests/` and `packages/graphrag-vectors/tests/__init__.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before QdrantVectorStore can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests (write first per Constitution Principle III — expect failures)

- [x] T003 [P] Add `VectorStoreType.Qdrant = "qdrant"` to `packages/graphrag-vectors/graphrag_vectors/vector_store_type.py`
- [x] T004 [P] Add unit test for Qdrant enum value in `packages/graphrag-vectors/tests/test_vector_store_type.py` — verify `VectorStoreType.Qdrant.value == "qdrant"` and `VectorStoreType.Qdrant` is discoverable
- [x] T005 Add Qdrant-specific config fields (`distance`, `hnsw_m`, `hnsw_ef_construct`, `hnsw_ef`) to `packages/graphrag-vectors/graphrag_vectors/vector_store_config.py` as optional fields — these are allowed via `extra="allow"` so explicit fields are optional but improve type hints and documentation
- [x] T006 [P] Add unit tests for Qdrant config fields in `packages/graphrag-vectors/tests/test_vector_store_config.py` — verify fields are accepted and passed through `model_dump()`

### Implementation

- [x] T007 [P] Implement `QdrantVectorStore` class skeleton in `packages/graphrag-vectors/graphrag_vectors/qdrant.py` — import `VectorStore`, `VectorStoreDocument`, `VectorStoreSearchResult` from parent package, define class inheriting `VectorStore`, add `__init__` with all inherited + Qdrant-specific fields
- [x] T008 Implement `connect()` method in `qdrant.py` — create `QdrantClient(url=..., api_key=...)` or `QdrantClient(path=:memory:)` for local testing; set `_client` attribute; raise `ValueError` if `url` not provided
- [x] T009 Implement `create_index()` method in `qdrant.py` — delete existing collection if present; create collection with `VectorParams(size=vector_size, distance=<Distance enum>)`; apply `HnswConfigDiff` if HNSW params configured; raise `ValueError` if `index_name` is empty
- [x] T010 Implement `_compile_filter()` and `_compile_condition()` methods in `qdrant.py` — map `FilterExpr` (Condition, AndExpr, OrExpr, NotExpr) to Qdrant `Filter`/`FieldCondition`; use match statement pattern identical to LanceDB/Azure AI Search/CosmosDB implementations
- [x] T011 Implement `load_documents()` method in `qdrant.py` — build `PointStruct` list from `VectorStoreDocument` objects; skip documents with `vector=None`; batch into chunks of 1000; upsert via `client.upsert()`
- [x] T012 Implement `similarity_search_by_vector()` method in `qdrant.py` — call `client.query_points()` with compiled filter; map Qdrant `ScoredPoint` to `VectorStoreSearchResult`; handle `select`, `include_vectors`, score normalization per distance metric
- [x] T013 Implement `search_by_id()` method in `qdrant.py` — call `client.retrieve()`; raise `IndexError` if not found; consistent with LanceDB behavior
- [x] T014 Implement `count()`, `remove()`, `update()` methods in `qdrant.py` — `count()` uses `client.count(exact=True)`; `remove()` uses `client.delete()`; `update()` reads existing point, merges fields, upserts
- [x] T015 Register Qdrant in `VectorStoreFactory` lazy-load in `packages/graphrag-vectors/graphrag_vectors/vector_store_factory.py` — add `case VectorStoreType.Qdrant:` branch importing from `qdrant` and calling `register_vector_store()`
- [x] T016 Export `QdrantVectorStore` from `packages/graphrag-vectors/graphrag_vectors/__init__.py` — add to `__all__` list
- [x] T017 [P] Add integration test for factory registration in `tests/integration/vector_stores/test_qdrant.py` — verify `VectorStoreFactory().create()` instantiates `QdrantVectorStore` with minimal config; verify `VectorStoreType.Qdrant` in factory keys
- [x] T018 [P] Implement unit tests for QdrantVectorStore core methods in `packages/graphrag-vectors/tests/test_qdrant.py` — test connect, create_index, load_documents, search, count, remove, update using `QdrantClient(":memory:")`; test all filter operators (eq, ne, gt, gte, lt, lte, in_, not_in, contains, startswith, endswith, exists, AND, OR, NOT); test batch upload with 1000+ documents; test error handling for missing URL, empty index_name
- [x] T019 Implement integration tests for QdrantVectorStore with Docker Qdrant in `tests/integration/vector_stores/test_qdrant.py` — same test coverage as `test_lancedb.py` pattern: basic operations, metadata fields, filtering, similarity search ordering, timestamp auto-setting, custom HNSW params, search_by_id with select/include_vectors, remove, update

### Checkpoint: Foundation ready — QdrantVectorStore implements all VectorStore ABC methods

---

## Phase 3: User Story 1 - Configure and Use Qdrant as Vector Backend (Priority: P1) 🎯 MVP

**Goal**: Users can configure and use Qdrant as the vector storage backend for GraphRAG indexing and querying workflows, supporting both local and Qdrant Cloud deployments.

**Independent Test**: A user can set `vector_store.type: qdrant` in GraphRAG YAML with a Qdrant URL, run the indexing pipeline, and verify embeddings are stored in Qdrant and retrievable via similarity search.

### Implementation

- [x] T020 [US1] Verify `graphrag/config/defaults.py` works with Qdrant config — no changes needed (same `url`/`api_key` pattern), add smoke test in `tests/smoke/` that creates a minimal GraphRAG config with `vector_store.type: qdrant` and validates it parses without errors
- [x] T021 [US1] Verify `graphrag/index/operations/embed_text/embed_text.py` workflow works with Qdrant — mock test that passes a QdrantVectorStore instance and verifies `embed_text()` calls `create_index()` and `load_documents()` correctly
- [x] T022 [US1] Verify `graphrag/utils/api.py` `create_vector_store()` wrapper works with Qdrant — test that `create_vector_store(config, index_schema)` returns a connected QdrantVectorStore with correct parameters

### Checkpoint: At this point, User Story 1 should be fully functional and testable independently — a user can configure Qdrant and use it for GraphRAG indexing and querying

---

## Phase 4: User Story 2 - Migrate Existing Workflows to Qdrant (Priority: P2)

**Goal**: Users can switch between LanceDB and Qdrant (or vice versa) by changing only configuration, without any code changes, and all existing workflows produce equivalent results.

**Independent Test**: Run the same GraphRAG index with `vector_store.type: lancedb` and `vector_store.type: qdrant` and get equivalent search result quality.

### Implementation

- [x] T023 [US2] Verify backward compatibility — run existing LanceDB integration tests (all tests in `tests/integration/vector_stores/test_lancedb.py`) and confirm they still pass — no regressions from adding Qdrant
- [x] T024 [US2] Verify Azure AI Search and CosmosDB integration tests still pass — confirm no cross-contamination from Qdrant lazy-load registration
- [x] T025 [US2] Verify `EntityVectorStoreKey` usage in query modules works with Qdrant — check `graphrag/query/context_builder/entity_extraction.py` and related modules use the VectorStore interface correctly regardless of backend
- [x] T026 [US2] Add cross-backend consistency test in `tests/integration/vector_stores/test_qdrant.py` — create identical embeddings in both LanceDB and Qdrant, run same similarity query, verify top-K results overlap significantly (score correlation > 0.95)

### Checkpoint: User Stories 1 AND 2 both work independently — switching vector store types is a pure config change

---

## Phase 5: User Story 3 - Leverage Qdrant-Specific Features (Priority: P3)

**Goal**: Power users can configure HNSW index parameters for performance tuning and benefit from Qdrant's native filtering on rich metadata.

**Independent Test**: An operator can configure custom HNSW parameters and verify search performance characteristics change accordingly.

### Implementation

- [x] T027 [US3] Verify HNSW parameter passthrough works end-to-end — in `packages/graphrag-vectors/tests/test_qdrant.py`, test that `hnsw_m`, `hnsw_ef_construct`, and `hnsw_ef` are passed to `client.create_collection()` as `HnswConfigDiff`
- [x] T028 [US3] Verify custom distance metric support — test `distance=Distance.DOT` and `distance=Distance.EUCLID` in create_index and search; verify score interpretation matches Qdrant behavior
- [x] T029 [US3] Add smoke test for Qdrant Cloud configuration — create config with `url` pointing to a fake cloud URL and `api_key` set, verify `QdrantClient` is instantiated with correct auth headers (no network call, just construction test)
- [x] T030 [US3] Update `quickstart.md` with advanced configuration examples — HNSW params, custom distance, Qdrant Cloud, batch size tuning

### Checkpoint: All user stories complete — Qdrant supports advanced features

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Finalize documentation, add versioning, ensure full compliance

- [x] T031 Run full test suite `uv run poe test` — verify all 45+ existing tests pass + new Qdrant tests pass
- [x] T032 Run `uv run poe check` — verify 0 lint errors, 0 pyright errors, all files formatted (note: pre-existing RUF067 issue in graphrag-llm/__init__.py unrelated to this feature)
- [ ] T033 [P] Add semversioner change entry for `graphrag-vectors` — `uv run semversioner add-change -t minor -p graphrag-vectors -d "Add Qdrant as fourth vector store backend."`
- [x] T034 Update `AGENTS.md` with Qdrant technology info (auto-done by update-agent-context.sh, verify it was applied)
- [ ] T035 [P] Update `docs/research/packages_todos.md` to mark P3 as completed
- [ ] T036 Validate quickstart.md steps work end-to-end — docker run Qdrant, create config, verify curl health check

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - US1 must complete before US2 and US3 (US2 tests migration FROM LanceDB TO Qdrant; US3 builds on US1)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — MVP delivery
- **US2 (P2)**: Depends on US1 (validates migration FROM LanceDB TO Qdrant)
- **US3 (P3)**: Depends on US1 (advanced features build on core functionality)

### Parallel Opportunities

- Phase 1: T001, T002 can run in parallel
- Phase 2: T003, T004 parallel; T005, T006 parallel; T007-T014 sequential (implementation chain); T015-T019 after T007-T014
- Phase 3: T020-T022 can run in parallel (all verify different integration points)
- Phase 4: T023, T024, T025, T026 can run in parallel
- Phase 5: T027-T030 can run in parallel

---

## Parallel Example: Foundational Phase (T003-T006)

```bash
# Launch enum test + config test in parallel:
Task: "Add VectorStoreType.Qdrant = 'qdrant' to vector_store_type.py"
Task: "Add unit test for Qdrant enum value"

Task: "Add Qdrant config fields to vector_store_config.py"
Task: "Add unit tests for Qdrant config fields"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T019) — CORE: QdrantVectorStore fully implemented + tested
3. Complete Phase 3: US1 (T020-T022) — Integration with GraphRAG pipeline
4. **STOP and VALIDATE**: Configure Qdrant in a test GraphRAG project, run indexing, run query, verify results
5. This delivers a fully functional Qdrant backend

### Incremental Delivery

1. Setup + Foundational → QdrantVectorStore is a first-class vector store
2. Add US1 → GraphRAG indexing + querying works with Qdrant (MVP!)
3. Add US2 → Confirmed backward compatibility + cross-backend equivalence
4. Add US3 → Advanced HNSW/distance customization available
5. Polish → Production-ready documentation and compliance

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (integration with graphrag package)
   - Developer B: User Story 2 (backward compatibility verification)
   - Developer C: User Story 3 (advanced features)
3. Stories complete sequentially (US1 → US2 → US3 due to dependencies)

---

## Notes

- T003 is the FIRST step of the Red-Green-Refactor cycle: add enum, write test, run test (expect failure), implement, run test (expect pass)
- T018 is the largest task — comprehensive unit test suite using in-memory Qdrant
- T019 mirrors the existing `test_lancedb.py` structure for consistency
- Constitution Principle III (Test-First) is enforced: all test tasks (T004-T006, T017-T019) MUST be written before their corresponding implementation tasks
- All tasks use absolute file paths matching the actual repository layout
