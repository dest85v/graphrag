# Implementation Plan: Qdrant Vector Store Support

**Branch**: `003-003-qdrant-vector` | **Date**: 2026-04-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-qdrant-vector-db/spec.md`

## Summary

Add Qdrant as the fourth vector store backend for GraphRAG, alongside existing LanceDB, Azure AI Search, and CosmosDB. The implementation adds a `QdrantVectorStore` class in the `graphrag-vectors` package that implements the existing `VectorStore` ABC, registers itself in `VectorStoreType` enum and `VectorStoreFactory`, and supports local and cloud Qdrant deployments with full filter, metadata, and batch upload capabilities.

## Technical Context

**Language/Version**: Python 3.11–3.13 (per project `requires-python = ">=3.11,<3.14"`)  
**Primary Dependencies**: `qdrant-client>=1.7.0,<1.18.0` (optional `qdrant` extra in `graphrag-vectors`)  
**Storage**: Qdrant (external, remote or local via Docker)  
**Testing**: pytest with `asyncio_mode = "auto"`, 1000s timeout; integration tests in `tests/integration/vector_stores/`  
**Target Platform**: Linux server, any platform with Docker  
**Project Type**: Library (monorepo, 8 packages) — `graphrag-vectors` is the package being extended  
**Performance Goals**: Batch upload of 100K+ vectors with metadata in under 5 minutes; HNSW-configurable search latency  
**Constraints**: Must not change the `VectorStore` ABC; must not break existing LanceDB/Azure AI Search/CosmosDB workflows; must use existing `FilterExpr` compilation pattern  
**Scale/Scope**: Single vector store implementation + factory registration + config + tests; ~600 lines of new code (aligned with existing Azure AI Search ~373 lines, CosmosDB ~421 lines, LanceDB ~272 lines)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance | Notes |
|-----------|------------|-------|
| **I. Library-First Architecture** | ✅ PASS | Qdrant implementation lives in `graphrag-vectors` package (already exists). Self-contained, independently testable, communicates via `VectorStore` ABC |
| **II. CLI Interface** | ✅ PASS | Vector store selection is config-driven (`vector_store.type: qdrant`); no CLI changes needed — GraphRAG CLI already passes vector store config to pipeline |
| **III. Test-First (NON-NEGOTIABLE)** | ✅ PASS | Tests will be written before implementation per Red-Green-Refactor. New tests in `tests/unit/` and `tests/integration/vector_stores/` |
| **IV. Integration Testing** | ✅ PASS | Integration tests added to `tests/integration/vector_stores/test_qdrant.py` alongside existing store tests. Validates cross-package workflow (graphrag-vectors → graphrag indexing → graphrag query) |
| **V. Versioning & Change Management** | ✅ PASS | `graphrag-vectors` version will be bumped (minor) with `semversioner add-change`. No breaking changes to public API |

**Result**: All gates pass. No complexity justifications needed — this follows the established pattern for adding vector store types (see Azure AI Search and CosmosDB additions).

## Project Structure

### Documentation (this feature)

```text
specs/003-qdrant-vector-db/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
packages/graphrag-vectors/graphrag_vectors/
├── vector_store_type.py          # ADD: Qdrant = "qdrant"
├── vector_store_config.py        # ADD: qdrant-specific fields (collection_name, hnsw_cfg, distance)
├── qdrant.py                     # NEW: QdrantVectorStore implementation (~500 lines)
├── vector_store_factory.py       # ADD: lazy-load case for Qdrant
├── __init__.py                   # ADD: QdrantVectorStore export

packages/graphrag-vectors/tests/  # NEW directory
└── test_qdrant.py                # NEW: unit + integration tests for QdrantVectorStore

tests/integration/vector_stores/
└── test_qdrant.py                # NEW: integration tests (local Qdrant via Docker)
```

### Configuration Changes

```text
packages/graphrag-vectors/pyproject.toml
└── ADD: [project.optional-dependencies] qdrant = ["qdrant-client>=1.7.0,<1.18.0"]

packages/graphrag/graphrag/config/defaults.py
└── No changes needed — Qdrant uses same `db_uri`/`url`/`api_key` pattern as existing stores
```

**Structure Decision**: Follow the existing 3-store pattern exactly. `qdrant.py` is a sibling module to `lancedb.py`, `azure_ai_search.py`, and `cosmosdb.py` inside `graphrag_vectors/`. The `VectorStoreType` enum gets a `Qdrant` member. Factory lazy-loads Qdrant on first use. Tests mirror existing store test structure. No architectural deviation from established patterns.

## Complexity Tracking

> **Not applicable** — This feature follows the established pattern for adding vector store types. No novel architectural decisions needed. The `VectorStore` ABC, `FilterExpr` system, and factory pattern are all reusable as-is.
